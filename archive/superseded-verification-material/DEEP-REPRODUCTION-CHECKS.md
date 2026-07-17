# Deeper focused reproduction checks

This second-pass script targets state-machine, queue, callback, persistence and routing defects found after the initial 17 July audit pass.

## Run command

```bash
OPENHOP_REPEATER_ROOT=/path/to/openhop_repeater \
OPENHOP_CORE_ROOT=/path/to/openhop_core \
  python /path/to/audit/docs/DEEP-REPRODUCTION-CHECKS.py
```

## Covered claims

1. Failed companion fan-out is still recorded as delivered.
2. A companion exception prevents another colliding local identity from running.
3. MQTT invalid-packet suppression is ignored.
4. The raw duplicate path bypasses the nested duplicate cap.
5. Live reload changes the deduplication TTL default and removes its minimum.
6. `update_nested()` clobbers sibling keys for deep paths.
7. OpenAPI duty-cycle fields differ from the implemented endpoint.
8. A version check can overwrite an active install state.
9. A stale check result can be attached to a newly selected channel.
10. Channel persistence failure is reported as success.
11. Password-save failure leaves the new runtime password active.
12. Enhanced raw callback exceptions cause a second invocation.
13. Awaitables returned by synchronous callback wrappers are not awaited.
14. Offline messages are removed before outbound enqueue succeeds.
15. Async persistence can remove a different, newer message.

All **15** deeper checks passed against the supplied snapshots. Together with the original 12 focused checks, the audit now contains **27 focused reproductions**.
