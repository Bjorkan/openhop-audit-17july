# BUG-049 — Concurrent sends can bypass the client-repeat airtime budget gate

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | Airtime budget / send concurrency |
| Components | OpenHop Core |
| Audit date | 2026-07-18 |

## TL;DR

`send_packet()` checks the airtime budget before acquiring the transmission lock. The check only observes the current bucket; it does not reserve airtime. Budget is charged only after the radio send completes. Multiple concurrent callers can therefore all pass the same budget state, queue behind the TX lock, and transmit without rechecking after an earlier send has depleted the bucket and established pacing.

The reproduced path is source-level and uses the real `Dispatcher.send_packet()` entry point. It proves incorrect admission and pacing behavior in the supplied code; it does not claim a physical over-the-air duty-cycle measurement on radio hardware.

## Expected behavior

Every transmission admitted while client-repeat budgeting is enabled must be evaluated against the budget state left by earlier admitted or completed transmissions. TX serialization must not allow stale pre-lock admission decisions to bypass newly established pacing.

## Required direction

1. Make budget admission atomic with either a reservation or a final recheck immediately before transmission.
2. If airtime is reserved before radio completion, refund or reconcile the reservation on cancellation, radio failure and `None`/invalid send results.
3. Preserve the intentional non-client-repeat fast path and explicitly decide whether delayed client-repeat traffic may block ACK or companion traffic.
4. Add concurrent regression coverage; sequential budget tests cannot expose this race.

## Triple verification

| Method | Check | Result | Observation |
|---:|---|---|---|
| 1 | Static runtime trace | **Passed** | Admission occurs before `_tx_lock`, does not reserve budget, and charging occurs only after `radio.send()`. |
| 2 | Executable concurrent send | **Passed** | Two real `send_packet()` tasks both pass one 100 ms admission budget while the first radio send is blocked; both then transmit successfully. |
| 3 | Active falsification and control | **Passed** | The same budget correctly delays a second send when calls are sequential, proving the failure is specifically the concurrent pre-admission window rather than a broken basic gate. |

The executable check is preserved as [`docs/triple-verification/verify_bug_049.py`](../docs/triple-verification/verify_bug_049.py), with its captured output in [`verify_bug_049.out`](../docs/triple-verification/verify_bug_049.out).

## Implementation plan

See [`implementation-plans/BUG-049/implementation_plan.md`](../implementation-plans/BUG-049/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/node/dispatcher.py` lines 646–672

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L646-L672)

```text
  646 |     async def _await_tx_budget(self, packet: Packet) -> None:
  647 |         """Delay until the airtime budget allows this transmit; never drops.
  648 | 
  649 |         Reproduces the Dispatcher::checkSend TX gate: require at least
  650 |         ``est_airtime(MAX_TRANS_UNIT) / MIN_TX_BUDGET_AIRTIME_DIV`` of budget
  651 |         before sending, and honour the ``next_tx_time`` pacing that
  652 |         Dispatcher's send-complete path sets when the budget dips below
  653 |         MIN_TX_BUDGET_RESERVE_MS. When short, sleep for the firmware-computed
  654 |         ``needed / duty_cycle`` and re-check. Called before the TX lock is
  655 |         taken, so a waiting forward never blocks other transmits (ACKs,
  656 |         companion sends); asyncio.sleep is cancellation-safe and the budget is
  657 |         only mutated synchronously, so a cancelled wait leaves it consistent.
  658 |         """
  659 |         reserve_ms = self._tx_est_airtime_ms(MAX_TRANS_UNIT) / MIN_TX_BUDGET_AIRTIME_DIV
  660 |         while True:
  661 |             now = time.monotonic()
  662 |             self._refill_tx_budget(now)
  663 |             duty = self._duty_cycle()
  664 |             wait_ms = 0.0
  665 |             if self._tx_budget_ms < reserve_ms:
  666 |                 wait_ms = (reserve_ms - self._tx_budget_ms) / duty
  667 |             # next_tx_time pacing from the previous debit.
  668 |             pace_s = self._tx_next_time - now
  669 |             wait_s = max(wait_ms / 1000.0, pace_s)
  670 |             if wait_s <= 0.0:
  671 |                 return
  672 |             await asyncio.sleep(wait_s)
```

### Evidence 2: `src/openhop_core/node/dispatcher.py` lines 837–867

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L837-L867)

```text
  837 |     async def send_packet(
  838 |         self,
  839 |         packet: Packet,
  840 |         wait_for_ack: bool = True,
  841 |         expected_crc: Optional[int] = None,
  842 |     ) -> bool:
  843 |         """
  844 |         Send a packet and optionally wait for an ACK.
  845 |         Uses a lock to serialize transmissions instead of dropping packets.
  846 | 
  847 |         Args:
  848 |             packet: The packet to send
  849 |             wait_for_ack: Whether to wait for an ACK
  850 |             expected_crc: The expected CRC for ACK matching.
  851 |                 If None, will be calculated from packet.
  852 |         """
  853 |         # TRACE is only sent via sendDirect() in firmware; flood TRACE is unsupported.
  854 |         route_type = packet.get_route_type()
  855 |         if route_type in (ROUTE_TYPE_FLOOD, ROUTE_TYPE_TRANSPORT_FLOOD):
  856 |             if packet.get_payload_type() == PAYLOAD_TYPE_TRACE:
  857 |                 self._log("TRACE not supported for flood; dropping")
  858 |                 return False
  859 |         self._apply_flood_scope(packet)
  860 |         self._apply_default_path_hash_mode(packet)
  861 |         # Airtime duty-cycle budget: only while client-repeat is on. Waiting
  862 |         # here (before the TX lock) keeps a throttled forward from blocking
  863 |         # other transmits. When disabled, the send path is unchanged.
  864 |         if self._client_repeat_enabled:
  865 |             await self._await_tx_budget(packet)
  866 |         async with self._tx_lock:  # Wait our turn
  867 |             return await self._send_packet_immediate(packet, wait_for_ack, expected_crc)
```

### Evidence 3: `src/openhop_core/node/dispatcher.py` lines 889–905

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L889-L905)

```text
  889 |         # ------------------------------------------------------------------ #
  890 |         self.state = DispatcherState.TRANSMIT
  891 |         raw = packet.write_to()
  892 |         tx_metadata = None
  893 |         try:
  894 |             tx_metadata = await self.radio.send(raw)
  895 |         except Exception as e:
  896 |             self._log(f"Radio transmit error: {e}")
  897 |             self.state = DispatcherState.IDLE
  898 |             return False
  899 |         if tx_metadata is None:
  900 |             self._log("Radio transmit returned no confirmation metadata")
  901 |             self.state = DispatcherState.IDLE
  902 |             return False
  903 |         # Spend the airtime budget on the completed transmit (client-repeat only).
  904 |         if self._client_repeat_enabled:
  905 |             self._debit_tx_budget(packet)
```
