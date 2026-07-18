# Verification notes — independently updated triple-verified deep review

Material classification corrections retained from the existing audit:

- `BUG-002` remains a retracted false positive because the shared API wrapper preserves the expected response envelope.
- `BUG-026` remains reclassified into `POSSIBLE-ENHANCEMENT-018`; destructive pop and backpressure shedding are documented semantics rather than a proven contract violation.
- `BUG-017` remains conditional and Medium severity.
- `BUG-018` remains a latent Low-severity helper-contract defect because no supplied call sites were found.
- `BUG-025` remains narrowed to callable objects and synchronous wrappers that return awaitables.

## 18 July independent update

- Every existing active report, reproduction, source reference, severity and plan was treated as untrusted and rechecked against the supplied snapshots.
- `BUG-028` through `BUG-049` have three independent checks each; `BUG-049` is the only newly added defect.
- Nine plausible-looking candidates are rejected or deferred because reachability, intent or an explicit contradictory contract was not established.
- Core passes **1,331/1,331** tests. Repeater runs **1,222** tests against the supplied Core and reports **1,221 passed, 1 failed, 7 warnings** due to an `airtime_factor` default expectation mismatch.
- BUG-028–BUG-049 source excerpts cover **1,530 lines across 60 ranges**; all active findings together contain **5,901 checked source lines with zero mismatches**.
- Fourteen existing evidence ranges were moved or regenerated to match the newer Core snapshot without changing the underlying findings.

The focused checks support the reports but do not replace regression tests in the owning repositories. Physical radio effects are not claimed as confirmed without hardware execution.
