# Triple-verification report — new findings

## Admission rule

No new bug in this edition was accepted from a lint warning, code smell or isolated helper discrepancy. Each report had to pass all three of the following, with the third check designed as a countercheck rather than a duplicate assertion:

1. **Static end-to-end trace** — writer/caller/consumer or lifecycle ownership was followed through the supplied source.
2. **Executable reproduction** — the incorrect result was produced using the real implementation and deterministic fakes only where hardware or transport was required.
3. **Active falsification** — the public/runtime path or an independent adapter/environment was exercised while actively looking for a documented policy, guard, wrapper, normalization, fallback or unreachable-state explanation that would invalidate the reproduction.

This process reduces false-positive risk but cannot mathematically guarantee behavior on every external firmware, operating system or later revision. Findings are confirmed against the two supplied snapshots.

## Results

| Finding | Severity | Checks | Specific static / executable / falsification checks |
|---|---:|---:|---|
| [BUG-028](../findings/BUG-028-wsradio-cannot-be-used-with-the-dispatcher.md) | High | 3/3 | Static contract trace, Dispatcher construction, Public node path |
| [BUG-029](../findings/BUG-029-successful-kiss-queueing-is-reported-as-send-failure.md) | Medium | 3/3 | Static contract contradiction, Direct adapter path, Dispatcher integration |
| [BUG-030](../findings/BUG-030-unterminated-kiss-rx-frames-grow-without-bound.md) | High | 3/3 | Bytewise decoder, Bulk decoder, Worker-like stream |
| [BUG-031](../findings/BUG-031-kiss-wait-for-rx-completes-an-asyncio-future-from-a-worker-thread.md) | High | 3/3 | Static thread-hop trace, Debug event loop, Release-loop wakeup |
| [BUG-032](../findings/BUG-032-meshnode-stop-does-not-stop-the-running-node.md) | Medium | 3/3 | Static lifecycle trace, Public stop call, Real dispatcher loop |
| [BUG-033](../findings/BUG-033-kiss-connection-state-remains-healthy-after-worker-or-config-failure.md) | High | 3/3 | Auto-config failure, TX-worker failure, Context manager |
| [BUG-034](../findings/BUG-034-failed-kiss-config-queueing-still-mutates-local-config.md) | Medium | 3/3 | Static operation order, Full queue, Wire-state countercheck |
| [BUG-035](../findings/BUG-035-concurrent-radio-commands-with-the-same-response-type-collide.md) | High | 3/3 | Static correlation key, TCP concurrency, USB concurrency |
| [BUG-036](../findings/BUG-036-usb-live-radio-settings-never-reach-the-modem.md) | High | 3/3 | Static setter trace, Direct setter, ConfigManager integration |
| [BUG-037](../findings/BUG-037-command-responses-use-one-global-unkeyed-slot.md) | High | 3/3 | Static unkeyed slot, Unrelated message, Overlapping public calls |
| [BUG-038](../findings/BUG-038-login-responses-use-one-global-unkeyed-slot.md) | High | 3/3 | Static state mismatch, Overlapping login, Cleanup interference |
| [BUG-039](../findings/BUG-039-frame-server-reconnect-removes-unrelated-push-listeners.md) | High | 3/3 | Static clear-all trace, Third-party listener, Reconnect path |
| [BUG-040](../findings/BUG-040-companion-preference-save-failures-are-reported-as-success.md) | Medium | 3/3 | Static return discard, Failed setter, Restart countercheck |
| [BUG-041](../findings/BUG-041-websocket-restart-can-create-duplicate-heartbeat-threads.md) | Medium | 3/3 | Static lifecycle trace, Immediate restart, Observable effect |
| [BUG-042](../findings/BUG-042-rrd-counter-rates-are-treated-as-cumulative-counters.md) | High | 3/3 | Static datasource/reader contradiction, Packet-type reader, Dashboard buckets |
| [BUG-043](../findings/BUG-043-sx1262-sync-word-is-never-programmed.md) | High | 3/3 | Static config-to-driver trace, Low-level call, Full initialization |
| [BUG-044](../findings/BUG-044-mesh-cli-uses-an-obsolete-save-return-contract.md) | High | 3/3 | Static signature/callsites, Real public command, Test-double countercheck |
| [BUG-045](../findings/BUG-045-mesh-cli-security-commands-write-the-wrong-config-section.md) | High | 3/3 | Static writer/reader mismatch, Command state separation, Actual LoginHelper |
| [BUG-046](../findings/BUG-046-mesh-cli-frequency-command-stores-mhz-as-hz.md) | High | 3/3 | Static help/getter/setter trace, Public command persistence, Live application |
| [BUG-047](../findings/BUG-047-local-advert-interval-is-saved-and-displayed-but-never-scheduled.md) | Medium | 3/3 | Static writer/telemetry/scheduler trace, Runtime reload, Actual timer decision |
| [BUG-048](../findings/BUG-048-mesh-cli-flood-advert-interval-writes-the-wrong-key.md) | Medium | 3/3 | Static key trace, Public command persistence, Runtime reload |
| [BUG-049](../findings/BUG-049-concurrent-sends-can-bypass-the-client-repeat-airtime-budget-gate.md) | High | 3/3 | Static runtime trace, Executable concurrent send, Sequential falsification control |

- Triple-verified reports in this continuation: **22**
- Independent passed checks: **66/66**
- Verification scripts: [`triple-verification/`](triple-verification/)
- Rejected/deferred candidates: [`REJECTED-CANDIDATES.md`](REJECTED-CANDIDATES.md)

## Full-suite context

Both complete project suites were rerun separately from clean processes after the 66 focused checks. Core collected **1,331 tests**, reached 100%, and exited with status 0. Repeater collected **1,222 tests** and completed with **1,221 passed, 1 failed and 7 warnings**. The single failure is an explicit cross-snapshot default mismatch: supplied Core returns `airtime_factor=1.0`, while `test_bridge_accepts_host_radio_callbacks` expects `0`. No incorrect runtime outcome was independently established, so the mismatch is documented in [`REJECTED-CANDIDATES.md`](REJECTED-CANDIDATES.md) rather than promoted to a bug. Outputs are preserved as [`CORE-FULL-RERUN-OUTPUT.txt`](CORE-FULL-RERUN-OUTPUT.txt), [`REPEATER-FULL-RERUN-OUTPUT.txt`](REPEATER-FULL-RERUN-OUTPUT.txt), [`CORE-TEST-COLLECTION-DEEP-REVIEW.txt`](CORE-TEST-COLLECTION-DEEP-REVIEW.txt) and [`REPEATER-TEST-COLLECTION-DEEP-REVIEW.txt`](REPEATER-TEST-COLLECTION-DEEP-REVIEW.txt).

Passing existing suites did not invalidate the reports: the new reproductions specifically demonstrate gaps in current coverage, including tests that mock an obsolete return signature.
