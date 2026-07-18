"""Triple verification for BUG-049.

Requires OPENHOP_CORE_ROOT to point at the supplied OpenHop Core source tree.
The checks use the real Dispatcher.send_packet path and a deterministic radio
adapter that preserves the asynchronous send boundary.
"""
from __future__ import annotations

import asyncio
import inspect
import os
import sys
from pathlib import Path

CORE_ROOT = Path(os.environ["OPENHOP_CORE_ROOT"]).resolve()
sys.path.insert(0, str(CORE_ROOT / "src"))

from openhop_core.node.dispatcher import Dispatcher  # noqa: E402
from openhop_core.protocol import Packet  # noqa: E402
from openhop_core.protocol.constants import PAYLOAD_TYPE_TXT_MSG, ROUTE_TYPE_FLOOD  # noqa: E402


class BlockingRadio:
    """Real Dispatcher adapter boundary with a controllable first TX completion."""

    spreading_factor = 7
    bandwidth = 125_000
    coding_rate = 5
    preamble_length = 8

    def __init__(self) -> None:
        self.rx_callback = None
        self.send_count = 0
        self.first_started = asyncio.Event()
        self.release_first = asyncio.Event()
        self.second_started = asyncio.Event()

    def set_rx_callback(self, callback) -> None:
        self.rx_callback = callback

    async def send(self, data: bytes):
        assert data
        self.send_count += 1
        if self.send_count == 1:
            self.first_started.set()
            await self.release_first.wait()
        elif self.send_count == 2:
            self.second_started.set()
        return {"queued": True}

    def get_last_rssi(self) -> int:
        return -70

    def get_last_snr(self) -> float:
        return 7.0


def packet() -> Packet:
    pkt = Packet()
    pkt.header = (PAYLOAD_TYPE_TXT_MSG << 2) | ROUTE_TYPE_FLOOD
    pkt.payload = bytearray(b"budget-race")
    pkt.payload_len = len(pkt.payload)
    return pkt


def configured_dispatcher(radio: BlockingRadio) -> Dispatcher:
    dispatcher = Dispatcher(radio)
    dispatcher.airtime_budget_factor = 1.0  # duty = 0.5
    dispatcher.set_client_repeat_enabled(True)
    # Reserve threshold = 100 ms; each completed TX spends 200 ms.
    dispatcher._tx_est_airtime_ms = lambda _length: 200.0
    dispatcher._tx_budget_ms = 100.0
    dispatcher._tx_budget_last_update = __import__("time").monotonic()
    dispatcher._tx_next_time = 0.0
    return dispatcher


def static_runtime_trace() -> None:
    source = inspect.getsource(Dispatcher.send_packet)
    immediate = inspect.getsource(Dispatcher._send_packet_immediate)
    gate = source.index("await self._await_tx_budget(packet)")
    lock = source.index("async with self._tx_lock")
    radio_send = immediate.index("await self.radio.send(raw)")
    debit = immediate.index("self._debit_tx_budget(packet)")
    assert gate < lock, "budget admission is not before the TX lock"
    assert radio_send < debit, "budget is not charged after radio completion"
    assert "_debit_tx_budget" not in inspect.getsource(Dispatcher._await_tx_budget)
    print("PASS 1/3 static runtime trace: gate precedes lock; no reservation; debit follows TX")


async def executable_reproduction() -> None:
    radio = BlockingRadio()
    dispatcher = configured_dispatcher(radio)
    admitted: list[str] = []
    original_gate = dispatcher._await_tx_budget

    async def observed_gate(pkt: Packet) -> None:
        await original_gate(pkt)
        admitted.append(asyncio.current_task().get_name())

    dispatcher._await_tx_budget = observed_gate
    first = asyncio.create_task(
        dispatcher.send_packet(packet(), wait_for_ack=False), name="first"
    )
    await asyncio.wait_for(radio.first_started.wait(), timeout=1)

    second = asyncio.create_task(
        dispatcher.send_packet(packet(), wait_for_ack=False), name="second"
    )
    for _ in range(20):
        if len(admitted) == 2:
            break
        await asyncio.sleep(0)

    assert admitted == ["first", "second"], admitted
    assert radio.send_count == 1, "TX lock should hold the second radio send"
    assert not radio.second_started.is_set()

    radio.release_first.set()
    results = await asyncio.wait_for(asyncio.gather(first, second), timeout=1)
    assert results == [True, True]
    assert radio.send_count == 2
    assert radio.second_started.is_set()
    print("PASS 2/3 executable reproduction: two concurrent sends passed one admission budget")


async def active_falsification() -> None:
    # Control: when the first send is allowed to complete before the second starts,
    # the first debit creates pacing and the second does not reach the radio.
    radio = BlockingRadio()
    dispatcher = configured_dispatcher(radio)
    first = asyncio.create_task(dispatcher.send_packet(packet(), wait_for_ack=False))
    await asyncio.wait_for(radio.first_started.wait(), timeout=1)
    radio.release_first.set()
    assert await asyncio.wait_for(first, timeout=1) is True
    assert dispatcher._tx_budget_ms == 0.0
    assert dispatcher._tx_next_time > __import__("time").monotonic()

    second = asyncio.create_task(dispatcher.send_packet(packet(), wait_for_ack=False))
    await asyncio.sleep(0.02)
    assert radio.send_count == 1, "sequential control unexpectedly bypassed pacing"
    second.cancel()
    try:
        await second
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError("cancelled sequential control did not cancel")

    # The TX lock therefore serializes radio I/O, but it cannot invalidate an
    # admission decision already made by a concurrent waiter outside the lock.
    assert not dispatcher._tx_lock.locked()
    print("PASS 3/3 active falsification: sequential gate works; only concurrent pre-admission bypasses it")


async def main() -> None:
    static_runtime_trace()
    await executable_reproduction()
    await active_falsification()
    print("BUG-049: 3/3 checks passed")


if __name__ == "__main__":
    asyncio.run(main())
