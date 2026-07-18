# Rejected and deferred candidates

These candidates were deliberately excluded from the confirmed-defect count because the audit could not satisfy the same three-check admission rule or because the supplied code documents the behavior as policy.

| Candidate | Decision | Reason |
|---|---|---|
| MQTT heartbeat duplicate after restart | **Rejected as active bug** | The publisher object is constructed/connected once and disconnected during collector close; no supported in-repository path reuses the same object after shutdown. Similar-looking code alone is insufficient. |
| GPIO re-registration can orphan an old thread | **Deferred** | A repeated-registration mechanism exists, but no supported runtime reconfiguration path was established against the supplied snapshot. |
| First companion bridge owns one SSE callback path | **Deferred** | The ownership model may be intentional; no contradictory public contract or clearly affected supported multi-identity path was established. |
| TCP fire-and-forget writes can appear successful before later failure | **Deferred** | The web path runs off the event-loop thread, while the Mesh CLI path is currently interrupted by confirmed BUG-044. Independent reachable impact was not proven without relying on another defect. |
| `airtime_factor`, `interference_threshold`, `agc_reset_interval` are written but have no found consumers | **Deferred** | Writer-only fields were found, but no explicit user contract or implementation intent strong enough to distinguish incomplete future work from a defect. |
| Generic `set radio` numeric units | **Deferred** | Unlike `set freq <mhz>`, the generic command help does not establish an unambiguous unit contract. |
| Repeated-high GPIO callback behavior | **Rejected** | Source comments describe it as an intentional hardware workaround. |
| CAD timeout assumes channel clear | **Rejected as policy issue** | The fallback is explicitly logged/documented as a policy. A safer default could be proposed separately, but the supplied contract does not make it a bug. |
| Core/Repeater `airtime_factor` default mismatch | **Insufficiently supported as a runtime bug** | The current Repeater suite proves a snapshot/test-contract mismatch: supplied Core defaults the preference to `1.0`, while one Repeater test expects `0`. Core comments describe `1.0` as the firmware companion default, while older documentation/test expectations still use `0`. Without a decisive supplied external contract or reproduced harmful runtime outcome, only the compatibility/test inconsistency is confirmed. |

A candidate should be promoted only after a real public path, contradictory contract and reproducible incorrect outcome are established independently.
