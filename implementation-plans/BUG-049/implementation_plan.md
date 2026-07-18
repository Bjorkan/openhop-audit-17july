# BUG-049 — implementation plan

[← Finding](../../findings/BUG-049-concurrent-sends-can-bypass-the-client-repeat-airtime-budget-gate.md) · [← Audit index](../../README.md)

> This is a planning document, not a ready-to-apply patch. Revalidate line numbers and surrounding code against the branch being changed.
> Verification status: **three independent checks passed against the supplied snapshots**.

| Field | Value |
|---|---|
| Finding | **Concurrent sends can bypass the client-repeat airtime budget gate** |
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | Airtime budget / send concurrency |
| Components | OpenHop Core |
| Audit date | 2026-07-18 |

## Objective

Ensure that every concurrently requested transmission is admitted against a current, non-stale airtime budget without weakening cancellation, radio-failure or non-client-repeat behavior.

## Current behavior

`Dispatcher.send_packet()` calls `_await_tx_budget()` before entering `_tx_lock`. `_await_tx_budget()` waits but does not reserve airtime. `_send_packet_immediate()` charges the bucket only after `radio.send()` returns metadata. Any number of tasks can therefore pass the same budget state before the first task completes and debits it; those tasks subsequently transmit under the TX lock without another budget check.

## Required outcome

A transmission may reach `radio.send()` only after an atomic admission decision that includes all earlier admitted transmissions. Failed or cancelled transmissions must not permanently consume reserved airtime, and a successful transmission must be charged exactly once.

## Repositories and files to inspect or change

| Repository | Path | Purpose |
|---|---|---|
| OpenHop Core | `src/openhop_core/node/dispatcher.py` | Owns budget state, admission, TX serialization and post-send charging |
| OpenHop Core | `tests/test_tx_budget.py` | Existing budget arithmetic and sequential send coverage; primary regression-test surface |
| OpenHop Core | `src/openhop_core/companion/companion_radio.py` | Applies live `airtime_factor` and client-repeat state; verify interactions with in-flight reservations |
| OpenHop Core | `tests/test_client_repeat.py` | Verify concurrent forwarded packets use the corrected send path without changing forwarding semantics |

Do not change the Repeater repository unless a concrete caller contract is found that requires it. The defect and its ownership are in Core.

## Implementation work packages

1. Choose one atomic admission model:
   - the smallest correctness change is a budget recheck after acquiring `_tx_lock` and immediately before `_send_packet_immediate()`; or
   - introduce a dedicated budget-admission lock plus explicit pending-airtime reservations if budget waits must not hold the TX lock.
2. Keep one charging model. If admission reserves estimated airtime, finalize rather than debit it a second time after success.
3. Reconcile reservations on every exit path: task cancellation, exception from `radio.send()`, `None` metadata, ACK timeout and shutdown.
4. Define how a live `airtime_factor` or client-repeat change affects waiters and reservations. Wake/recompute waiters rather than leaving them paced from stale parameters.
5. Preserve the exact no-budget path when client repeat is disabled.
6. Add bounded diagnostics for budget waits/reservations if needed for field verification; do not log each loop iteration.

## Decisions and assumptions to double-check

- [ ] Confirm whether the firmware-compatible budget is intended to govern every Core send while client repeat is enabled or only automatically forwarded packets.
- [ ] Confirm whether ACK/control traffic requires priority over budget-delayed forwarding. A simple lock-held sleep may preserve accounting but introduce priority inversion.
- [ ] Confirm whether estimated airtime or radio-reported airtime is authoritative when metadata contains a duration.
- [ ] Decide whether a queued radio submission counts as completed airtime for adapters that do not confirm physical TX.
- [ ] Verify that disabling client repeat with pending waiters cannot strand a reservation or leave `_tx_next_time` stale.
- [ ] Verify restart, shutdown and live-reload behavior: no reservation or waiter may survive cleanup incorrectly, and reloaded preferences must wake/recompute pending admissions.

## Test plan

### Existing test modules to extend

- OpenHop Core: `tests/test_tx_budget.py`
- OpenHop Core: `tests/test_client_repeat.py`

### Required focused tests

- [ ] Preserve verification method 1: assert the corrected code has atomic admission or an immediate post-lock recheck.
- [ ] Preserve verification method 2: start two concurrent `send_packet()` calls with budget sufficient for only one admission; the second must not reach `radio.send()` until the first debit/reservation has been incorporated and the calculated pacing delay has elapsed.
- [ ] Preserve verification method 3: retain a sequential control proving normal delay-not-drop behavior still works.
- [ ] Run a burst of many concurrent sends and prove aggregate admission cannot oversubscribe one bucket snapshot.
- [ ] Cancel a task while waiting, after reservation, and while queued for the TX lock; budget and locks must remain consistent.
- [ ] Make `radio.send()` raise and return `None`; any reservation must be refunded/reconciled exactly once.
- [ ] Change `airtime_factor` and client-repeat state while tasks are waiting; verify deterministic wake/recalculation behavior.
- [ ] Verify client-repeat disabled performs no budget calls, reservations or monotonic-clock reads beyond the existing hot path.
- [ ] Verify callback, packet accounting and ACK behavior remain exactly once per successful send.

### Integration verification

- [ ] Run the complete OpenHop Core suite in a clean process.
- [ ] Run the complete OpenHop Repeater suite against the same Core snapshot and resolve any cross-snapshot expectation mismatch separately.
- [ ] Run all preserved triple-verification scripts.
- [ ] On supported hardware, measure real TX spacing under a concurrent forwarding burst. This is required for physical duty-cycle confirmation but is not required to prove the source-level race.

## Compatibility, rollout and rollback

- Keep `send_packet()` return values and radio adapter contracts unchanged unless a separately coordinated contract correction is required.
- Avoid introducing an unbounded pending-reservation collection.
- If a new lock or condition is added, establish and document lock ordering relative to `_tx_lock` to prevent deadlocks.
- Roll out first on one client-repeat node with budget-wait diagnostics and retain a configuration rollback path.

## Definition of done

- [ ] No task can reach `radio.send()` using a budget decision made before an earlier admitted send changed the bucket or pacing state.
- [ ] Successful sends are charged exactly once; failed and cancelled sends leave consistent budget state.
- [ ] Concurrent, sequential, failure, cancellation and live-configuration tests pass.
- [ ] Client-repeat disabled behavior is unchanged.
- [ ] Complete Core tests pass, and the Repeater suite is run against the same Core revision with any independent mismatch documented.
