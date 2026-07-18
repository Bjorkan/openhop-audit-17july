from __future__ import annotations

import asyncio
import collections
import contextlib
import inspect
import os
import sys
import threading
import time
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

CORE = "/mnt/data/deep_audit_round2/core/openhop_core-fix-all-the-things-core/src"
REPEATER = "/mnt/data/deep_audit_round2/repeater/openhop_repeater-fix-all-the-things"
sys.path.insert(0, CORE)
sys.path.insert(0, REPEATER)

from openhop_core.hardware.base import LoRaRadio
from openhop_core.hardware.kiss_serial_wrapper import (
    KissSerialWrapper,
    KISS_CMD_DATA,
    KISS_CMD_TXDELAY,
    KISS_FEND,
    MAX_FRAME_SIZE,
    TX_BUFFER_SIZE,
)
from openhop_core.hardware.protocol_constants import CMD_CONFIG_RESP, CMD_SET_CONFIG
from openhop_core.hardware.tcp_radio import TCPLoRaRadio
from openhop_core.hardware.usb_radio import USBLoRaRadio
from openhop_core.hardware.wsradio import WsRadio
from openhop_core.node.dispatcher import Dispatcher
from openhop_core.node.node import MeshNode
from repeater.config import BaselineCrcCounterRadio
from repeater.config_manager import ConfigManager


@dataclass
class Check:
    finding: str
    method: str
    ok: bool
    detail: str


CHECKS: list[Check] = []


def check(finding: str, method: str, condition: bool, detail: str) -> None:
    CHECKS.append(Check(finding, method, bool(condition), detail))
    print(f"{'PASS' if condition else 'FAIL'} [{finding}] {method}: {detail}")


class FakePacket:
    def get_payload_type(self):
        return 0

    def calculate_packet_hash(self):
        return b"1234567890123456"

    def write_to(self):
        return b"payload"

    def get_raw_length(self):
        return 7

    def get_route_type(self):
        return 0


# FINDING A: WsRadio cannot be attached to Dispatcher/MeshNode.
def validate_wsradio_contract_static() -> None:
    missing = not hasattr(WsRadio, "set_rx_callback")
    dispatcher_src = inspect.getsource(Dispatcher.__init__)
    unconditional = "self.radio.set_rx_callback" in dispatcher_src
    fallback_src = inspect.getsource(Dispatcher.run_forever)
    fallback_unused = "_rx_once" not in fallback_src
    check(
        "WSRADIO-DISPATCHER-CONTRACT",
        "static-contract-trace",
        missing and unconditional and fallback_unused,
        f"missing_callback={missing}, unconditional_registration={unconditional}, run_forever_uses_fallback={not fallback_unused}",
    )


def validate_wsradio_contract_dynamic() -> None:
    radio = WsRadio(ip_address="127.0.0.1", port=1)
    exc = None
    try:
        Dispatcher(radio)
    except Exception as e:  # expected
        exc = e
    check(
        "WSRADIO-DISPATCHER-CONTRACT",
        "dispatcher-construction",
        isinstance(exc, AttributeError) and "set_rx_callback" in str(exc),
        f"exception={exc!r}",
    )


def validate_wsradio_contract_meshnode() -> None:
    radio = WsRadio(ip_address="127.0.0.1", port=1)
    identity = SimpleNamespace()
    exc = None
    try:
        MeshNode(radio, identity, config={})
    except Exception as e:
        exc = e
    check(
        "WSRADIO-DISPATCHER-CONTRACT",
        "public-meshnode-path",
        isinstance(exc, AttributeError) and "set_rx_callback" in str(exc),
        f"exception={exc!r}",
    )


# FINDING B: metadata-less success is rejected by Dispatcher.
def validate_no_metadata_contract_static() -> None:
    base_doc = inspect.getsource(LoRaRadio.send)
    kiss_doc = inspect.getsource(KissSerialWrapper.send)
    dispatch_src = inspect.getsource(Dispatcher._send_packet_immediate)
    check(
        "NO-METADATA-SEND-REJECTED",
        "static-contract-contradiction",
        "or None" in base_doc and "Returns None" in kiss_doc and "if tx_metadata is None" in dispatch_src,
        "LoRaRadio permits None; KISS returns None after queue success; Dispatcher treats None as failure",
    )


async def validate_no_metadata_direct_and_dispatcher() -> None:
    radio = KissSerialWrapper.__new__(KissSerialWrapper)
    queued: list[bytes] = []
    radio.send_frame = lambda data: queued.append(data) is None or True
    # lambda above returns True because expression resolves True? Make explicit below.
    def send_frame(data: bytes) -> bool:
        queued.append(data)
        return True
    radio.send_frame = send_frame
    radio.on_frame_received = None
    direct = await radio.send(b"abc")
    dispatcher = Dispatcher(radio)
    result = await dispatcher.send_packet(FakePacket(), wait_for_ack=False)
    check(
        "NO-METADATA-SEND-REJECTED",
        "direct-wrapper-success",
        direct is None and queued == [b"abc", b"payload"],
        f"direct_return={direct!r}, queued={queued!r}",
    )
    check(
        "NO-METADATA-SEND-REJECTED",
        "dispatcher-integration",
        result is False and queued[-1] == b"payload",
        f"physical_queue_success=True, dispatcher_result={result}",
    )


# FINDING C: KISS decoder has no maximum receive frame size.
def fresh_kiss_decoder() -> KissSerialWrapper:
    radio = KissSerialWrapper.__new__(KissSerialWrapper)
    radio.rx_frame_buffer = bytearray()
    radio.in_frame = False
    radio.escaped = False
    radio.kiss_port = 0
    radio.on_frame_received = None
    radio.stats = {"frame_errors": 0, "frames_received": 0, "bytes_received": 0}
    radio._process_received_frame = lambda: None
    return radio


def validate_kiss_rx_bound_bytewise() -> None:
    radio = fresh_kiss_decoder()
    radio._decode_kiss_byte(KISS_FEND)
    for _ in range(MAX_FRAME_SIZE * 20):
        radio._decode_kiss_byte(ord("A"))
    check(
        "KISS-UNBOUNDED-RX-FRAME",
        "bytewise-decoder",
        len(radio.rx_frame_buffer) == MAX_FRAME_SIZE * 20,
        f"buffer={len(radio.rx_frame_buffer)}, max={MAX_FRAME_SIZE}",
    )


def validate_kiss_rx_bound_bulk() -> None:
    radio = fresh_kiss_decoder()
    payload = b"B" * (MAX_FRAME_SIZE * 100)
    radio._decode_kiss(bytes([KISS_FEND]) + payload)
    check(
        "KISS-UNBOUNDED-RX-FRAME",
        "bulk-decoder",
        len(radio.rx_frame_buffer) == len(payload),
        f"buffer={len(radio.rx_frame_buffer)}, max={MAX_FRAME_SIZE}",
    )


def validate_kiss_rx_bound_chunked_stream() -> None:
    radio = fresh_kiss_decoder()
    radio._decode_kiss(bytes([KISS_FEND]))
    chunk = b"C" * 4096
    for _ in range(32):
        radio._decode_kiss(chunk)
    check(
        "KISS-UNBOUNDED-RX-FRAME",
        "worker-like-chunk-stream",
        len(radio.rx_frame_buffer) == len(chunk) * 32 and len(radio.rx_frame_buffer) > MAX_FRAME_SIZE,
        f"buffer={len(radio.rx_frame_buffer)}, max={MAX_FRAME_SIZE}",
    )


# FINDING D: wait_for_rx mutates an asyncio Future from the serial worker thread.
def validate_wait_for_rx_static() -> None:
    wait_src = inspect.getsource(KissSerialWrapper.wait_for_rx)
    worker_src = inspect.getsource(KissSerialWrapper._rx_worker)
    process_src = inspect.getsource(KissSerialWrapper._process_received_frame)
    check(
        "KISS-WAIT-FOR-RX-CROSS-THREAD",
        "static-thread-hop-trace",
        "future.set_result" in wait_src
        and "self._decode_kiss" in worker_src
        and "self.on_frame_received(data)" in process_src
        and "call_soon_threadsafe" not in wait_src,
        "RX worker invokes callback synchronously; callback directly calls Future.set_result",
    )


def validate_wait_for_rx_debug_loop() -> None:
    radio = KissSerialWrapper.__new__(KissSerialWrapper)
    radio.on_frame_received = None
    ready = threading.Event()
    loop_holder: dict[str, object] = {}
    cb_holder: dict[str, object] = {}
    finished = threading.Event()

    def runner_thread() -> None:
        loop = asyncio.new_event_loop()
        loop.set_debug(True)
        asyncio.set_event_loop(loop)
        loop_holder["loop"] = loop

        async def runner() -> None:
            task = asyncio.create_task(radio.wait_for_rx())
            await asyncio.sleep(0)
            cb_holder["callback"] = radio.on_frame_received
            cb_holder["task"] = task
            ready.set()
            try:
                await task
                finished.set()
            except asyncio.CancelledError:
                pass

        loop.create_task(runner())
        loop.run_forever()
        tasks = asyncio.all_tasks(loop)
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()

    thread = threading.Thread(target=runner_thread, daemon=True)
    thread.start()
    assert ready.wait(2)
    exc = None
    try:
        cb_holder["callback"](b"packet")
    except Exception as e:
        exc = e
    time.sleep(0.1)
    task = cb_holder["task"]
    check(
        "KISS-WAIT-FOR-RX-CROSS-THREAD",
        "debug-event-loop-runtime",
        isinstance(exc, RuntimeError) and not finished.is_set(),
        f"callback_exception={exc!r}, task_done={task.done()}, waiter_resumed={finished.is_set()}",
    )
    loop = loop_holder["loop"]
    loop.call_soon_threadsafe(loop.stop)
    thread.join(2)


def validate_wait_for_rx_release_loop_latency() -> None:
    radio = KissSerialWrapper.__new__(KissSerialWrapper)
    radio.on_frame_received = None
    ready = threading.Event()
    done = threading.Event()
    loop_holder: dict[str, object] = {}
    callback_holder: dict[str, object] = {}
    elapsed: dict[str, float] = {}

    def runner_thread() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop_holder["loop"] = loop

        async def runner() -> None:
            start = time.monotonic()
            task = asyncio.create_task(radio.wait_for_rx())
            await asyncio.sleep(0)
            callback_holder["cb"] = radio.on_frame_received
            ready.set()
            try:
                await task
                elapsed["value"] = time.monotonic() - start
                done.set()
            except asyncio.CancelledError:
                pass

        loop.create_task(runner())
        loop.run_forever()
        tasks = asyncio.all_tasks(loop)
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()

    thread = threading.Thread(target=runner_thread, daemon=True)
    thread.start()
    assert ready.wait(2)
    callback_holder["cb"](b"packet")
    # Without a thread-safe wakeup the loop remains asleep. An external nudge wakes it.
    early = done.wait(0.15)
    loop = loop_holder["loop"]
    loop.call_soon_threadsafe(lambda: None)
    late = done.wait(1.0)
    check(
        "KISS-WAIT-FOR-RX-CROSS-THREAD",
        "release-loop-wakeup-behaviour",
        not early and late,
        f"resumed_before_threadsafe_nudge={early}, resumed_after_nudge={late}, elapsed={elapsed.get('value')}",
    )
    loop.call_soon_threadsafe(loop.stop)
    thread.join(2)


# FINDING E: MeshNode.stop is a no-op while start blocks forever.
def validate_meshnode_stop_static() -> None:
    start_src = inspect.getsource(MeshNode.start)
    stop_src = inspect.getsource(MeshNode.stop)
    loop_src = inspect.getsource(Dispatcher.run_forever)
    check(
        "MESHNODE-STOP-NOOP",
        "static-lifecycle-trace",
        "run_forever" in start_src
        and "while True" in loop_src
        and "cancel" not in stop_src
        and "self.dispatcher" not in stop_src and "cancel" not in stop_src,
        "start awaits an infinite loop; stop only logs",
    )


async def validate_meshnode_stop_fake_dispatcher() -> None:
    entered = asyncio.Event()

    class BlockingDispatcher:
        async def run_forever(self):
            entered.set()
            await asyncio.Event().wait()

    node = MeshNode.__new__(MeshNode)
    node.dispatcher = BlockingDispatcher()
    node.logger = SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None)
    task = asyncio.create_task(node.start())
    await entered.wait()
    node.stop()
    await asyncio.sleep(0.05)
    check(
        "MESHNODE-STOP-NOOP",
        "public-stop-call",
        not task.done(),
        f"start_task_done_after_stop={task.done()}",
    )
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


async def validate_meshnode_stop_real_dispatcher() -> None:
    class FakeRadio:
        def set_rx_callback(self, cb):
            self.cb = cb

        async def send(self, data):
            return {"airtime_ms": 0}

        async def wait_for_rx(self):
            await asyncio.Event().wait()

    node = MeshNode.__new__(MeshNode)
    node.logger = SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None)
    node.dispatcher = Dispatcher(FakeRadio())
    task = asyncio.create_task(node.start())
    await asyncio.sleep(0.03)
    node.stop()
    await asyncio.sleep(0.03)
    check(
        "MESHNODE-STOP-NOOP",
        "real-dispatcher-loop",
        not task.done() and node.dispatcher.state is not None,
        f"dispatcher_task_done={task.done()}",
    )
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


# FINDING F: KISS connection and worker failure paths leave stale connected state/resources.
class FakeSerial:
    def __init__(self, *args, **kwargs):
        self.is_open = True
        self.in_waiting = 0
        self.closed = False

    def close(self):
        self.is_open = False
        self.closed = True

    def read(self, n):
        return b""

    def write(self, data):
        return len(data)

    def flush(self):
        pass


class FakeThread:
    instances: list["FakeThread"] = []

    def __init__(self, target=None, daemon=None, **kwargs):
        self.target = target
        self.started = False
        self.__class__.instances.append(self)

    def start(self):
        self.started = True

    def is_alive(self):
        return self.started

    def join(self, timeout=None):
        pass


def validate_kiss_connect_failure_cleanup() -> None:
    FakeThread.instances.clear()
    radio = KissSerialWrapper("/dev/fake", auto_configure=True)
    radio.configure_radio_and_enter_kiss = lambda: False
    with patch("openhop_core.hardware.kiss_serial_wrapper.serial.Serial", FakeSerial), patch(
        "openhop_core.hardware.kiss_serial_wrapper.threading.Thread", FakeThread
    ):
        result = radio.connect()
    check(
        "KISS-STALE-CONNECTION-STATE",
        "auto-config-failure",
        result is False
        and radio.is_connected is True
        and radio.serial_conn is not None
        and radio.serial_conn.is_open
        and all(t.started for t in FakeThread.instances),
        f"result={result}, connected={radio.is_connected}, serial_open={radio.serial_conn.is_open}, threads_started={[t.started for t in FakeThread.instances]}",
    )
    radio.disconnect()


def validate_kiss_tx_worker_failure_state() -> None:
    class ExplodingSerial:
        is_open = True

        def write(self, data):
            raise OSError("cable removed")

        def flush(self):
            pass

    radio = KissSerialWrapper.__new__(KissSerialWrapper)
    radio.stop_event = threading.Event()
    radio.is_connected = True
    radio.serial_conn = ExplodingSerial()
    radio.tx_buffer = collections.deque([b"frame"], maxlen=TX_BUFFER_SIZE)
    radio.stats = {"frames_sent": 0, "bytes_sent": 0, "buffer_overruns": 0}
    radio.kiss_port = 0
    radio._tx_worker()
    queued_after = radio.send_frame(b"abc")
    check(
        "KISS-STALE-CONNECTION-STATE",
        "tx-worker-exception",
        radio.is_connected is True and queued_after is True and len(radio.tx_buffer) == 1,
        f"worker_exited=True, connected={radio.is_connected}, later_queue_accept={queued_after}, queue_len={len(radio.tx_buffer)}",
    )


def validate_kiss_context_manager_failure() -> None:
    radio = KissSerialWrapper("/dev/fake", auto_configure=True)
    radio.connect = lambda: False
    entered = None
    exc = None
    try:
        with radio as entered_value:
            entered = entered_value
    except Exception as e:
        exc = e
    check(
        "KISS-STALE-CONNECTION-STATE",
        "context-manager-contract",
        exc is None and entered is radio,
        f"connect_return=False, context_entered={entered is radio}, exception={exc!r}",
    )


# FINDING G: local config mutates even when a KISS config command is rejected.
def validate_kiss_config_failed_queue() -> None:
    radio = KissSerialWrapper("/dev/fake", auto_configure=False)
    radio.is_connected = True
    radio.tx_buffer.extend([b"x"] * TX_BUFFER_SIZE)
    before = radio.get_config()["txdelay"]
    result = radio.send_config_command(KISS_CMD_TXDELAY, before + 10)
    after = radio.get_config()["txdelay"]
    check(
        "KISS-CONFIG-MUTATED-ON-QUEUE-FAILURE",
        "full-queue-runtime",
        result is False and after == before + 10 and len(radio.tx_buffer) == TX_BUFFER_SIZE,
        f"result={result}, before={before}, after={after}, queued={len(radio.tx_buffer)}",
    )


def validate_kiss_config_static_order() -> None:
    src = inspect.getsource(KissSerialWrapper.send_config_command)
    update_index = src.index("self.config")
    capacity_index = src.index("len(self.tx_buffer)")
    check(
        "KISS-CONFIG-MUTATED-ON-QUEUE-FAILURE",
        "static-operation-order",
        update_index < capacity_index,
        f"config_update_offset={update_index}, queue_capacity_check_offset={capacity_index}",
    )


def validate_kiss_config_no_wire_effect() -> None:
    radio = KissSerialWrapper("/dev/fake", auto_configure=False)
    radio.is_connected = True
    sentinel = b"sentinel"
    radio.tx_buffer.extend([sentinel] * TX_BUFFER_SIZE)
    result = radio.send_config_command(KISS_CMD_TXDELAY, 99)
    encoded_config_present = any(frame != sentinel for frame in radio.tx_buffer)
    check(
        "KISS-CONFIG-MUTATED-ON-QUEUE-FAILURE",
        "wire-state-countercheck",
        result is False and radio.get_config()["txdelay"] == 99 and not encoded_config_present,
        f"local={radio.get_config()['txdelay']}, new_command_present={encoded_config_present}",
    )


# FINDING H: same-response command waiters overwrite one another.
class OpenSerial:
    is_open = True

    def __init__(self):
        self.frames: list[bytes] = []

    def write(self, data):
        self.frames.append(bytes(data))
        return len(data)

    def flush(self):
        pass


async def exercise_response_collision(radio, transport: str) -> tuple[object, object, int]:
    loop = asyncio.get_running_loop()
    radio._event_loop = loop
    if transport == "tcp":
        radio._sock = object()
        sent: list[bytes] = []
        radio._sock_write = lambda frame: sent.append(bytes(frame))
    else:
        serial = OpenSerial()
        radio._serial = serial
        sent = serial.frames

    t1 = asyncio.create_task(
        radio._send_command(CMD_SET_CONFIG, b"first", CMD_CONFIG_RESP, timeout=0.2)
    )
    await asyncio.sleep(0)
    t2 = asyncio.create_task(
        radio._send_command(CMD_SET_CONFIG, b"second", CMD_CONFIG_RESP, timeout=0.2)
    )
    await asyncio.sleep(0)
    radio._dispatch_frame(CMD_CONFIG_RESP, b"one-response")
    r1, r2 = await asyncio.gather(t1, t2)
    return r1, r2, len(sent)


async def validate_tcp_response_collision() -> None:
    radio = TCPLoRaRadio("127.0.0.1")
    r1, r2, sent = await exercise_response_collision(radio, "tcp")
    check(
        "RADIO-RESPONSE-WAITER-COLLISION",
        "tcp-focused-concurrency",
        sent == 2 and [r1, r2].count(b"one-response") == 1 and [r1, r2].count(None) == 1,
        f"sent_commands={sent}, results={[r1, r2]!r}",
    )


async def validate_usb_response_collision() -> None:
    radio = USBLoRaRadio("/dev/fake")
    r1, r2, sent = await exercise_response_collision(radio, "usb")
    check(
        "RADIO-RESPONSE-WAITER-COLLISION",
        "usb-focused-concurrency",
        sent == 2 and [r1, r2].count(b"one-response") == 1 and [r1, r2].count(None) == 1,
        f"sent_commands={sent}, results={[r1, r2]!r}",
    )


def validate_response_collision_static() -> None:
    tcp_src = inspect.getsource(TCPLoRaRadio._send_command)
    usb_src = inspect.getsource(USBLoRaRadio._send_command)
    condition = all(
        "self._response_events[expect_cmd] = evt" in src and "async with" not in src
        for src in (tcp_src, usb_src)
    )
    check(
        "RADIO-RESPONSE-WAITER-COLLISION",
        "static-correlation-key",
        condition,
        "both drivers correlate only by expected command byte and have no command-level lock",
    )


# FINDING I: USB live setters acknowledge without writing config to modem.
def validate_usb_live_setters_static() -> None:
    setters = [
        inspect.getsource(USBLoRaRadio.set_frequency),
        inspect.getsource(USBLoRaRadio.set_tx_power),
        inspect.getsource(USBLoRaRadio.set_spreading_factor),
        inspect.getsource(USBLoRaRadio.set_bandwidth),
    ]
    no_transport = all("_send_command" not in s and "_serial.write" not in s and "return True" in s for s in setters)
    check(
        "USB-LIVE-CONFIG-NOT-PUSHED",
        "static-setter-trace",
        no_transport,
        "all ConfigManager-visible USB setters only mutate Python attributes and return True",
    )


def validate_usb_live_setters_direct() -> None:
    radio = USBLoRaRadio("/dev/fake")
    serial = OpenSerial()
    radio._serial = serial
    radio._initialized = True
    old = radio.frequency
    result = radio.set_frequency(old + 1000)
    check(
        "USB-LIVE-CONFIG-NOT-PUSHED",
        "direct-setter-runtime",
        result is True and radio.frequency == old + 1000 and serial.frames == [],
        f"result={result}, python_frequency={radio.frequency}, serial_writes={len(serial.frames)}",
    )


def validate_usb_live_configmanager_path() -> None:
    inner = USBLoRaRadio("/dev/fake")
    inner._serial = OpenSerial()
    inner._initialized = True
    proxy = BaselineCrcCounterRadio(inner)
    config = {
        "radio": {
            "frequency": inner.frequency + 2000,
            "bandwidth": inner.bandwidth + 1000,
            "spreading_factor": inner.spreading_factor + 1,
            "coding_rate": inner.coding_rate,
            "tx_power": inner.tx_power + 1,
            "preamble_length": inner.preamble_length,
            "sync_word": inner.sync_word,
        }
    }
    daemon = SimpleNamespace(radio=proxy, config=config, repeater_handler=None)
    manager = ConfigManager("/tmp/nonexistent-audit-config.yaml", config, daemon_instance=daemon)
    result = manager._apply_live_radio_config()
    check(
        "USB-LIVE-CONFIG-NOT-PUSHED",
        "repeater-config-manager-integration",
        result is True and inner._serial.frames == [] and inner.frequency == config["radio"]["frequency"],
        f"manager_result={result}, local_frequency={inner.frequency}, serial_writes={len(inner._serial.frames)}",
    )


async def main() -> None:
    validate_wsradio_contract_static()
    validate_wsradio_contract_dynamic()
    validate_wsradio_contract_meshnode()

    validate_no_metadata_contract_static()
    await validate_no_metadata_direct_and_dispatcher()

    validate_kiss_rx_bound_bytewise()
    validate_kiss_rx_bound_bulk()
    validate_kiss_rx_bound_chunked_stream()

    validate_wait_for_rx_static()
    validate_wait_for_rx_debug_loop()
    validate_wait_for_rx_release_loop_latency()

    validate_meshnode_stop_static()
    await validate_meshnode_stop_fake_dispatcher()
    await validate_meshnode_stop_real_dispatcher()

    validate_kiss_connect_failure_cleanup()
    validate_kiss_tx_worker_failure_state()
    validate_kiss_context_manager_failure()

    validate_kiss_config_static_order()
    validate_kiss_config_failed_queue()
    validate_kiss_config_no_wire_effect()

    validate_response_collision_static()
    await validate_tcp_response_collision()
    await validate_usb_response_collision()

    validate_usb_live_setters_static()
    validate_usb_live_setters_direct()
    validate_usb_live_configmanager_path()

    print("\nSUMMARY")
    by_finding: dict[str, list[Check]] = collections.defaultdict(list)
    for item in CHECKS:
        by_finding[item.finding].append(item)
    for finding, items in by_finding.items():
        passed = sum(i.ok for i in items)
        print(f"{finding}: {passed}/{len(items)}")
    failures = [item for item in CHECKS if not item.ok]
    if failures:
        raise SystemExit(f"{len(failures)} checks failed")


if __name__ == "__main__":
    asyncio.run(main())
