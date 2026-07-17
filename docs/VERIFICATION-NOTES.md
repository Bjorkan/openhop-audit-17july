# Verification notes — reverified edition

Material corrections to the previous audit:

- `BUG-002` was a false positive caused by omitting the shared API wrapper from the object-shape analysis.
- `BUG-026` described real loss behavior, but that behavior is consistent with the supplied documented destructive-pop and backpressure-shedding semantics. It is therefore reclassified into `POSSIBLE-ENHANCEMENT-018` rather than retained as a bug.
- `BUG-017` is conditional and its severity is reduced from High to Medium.
- `BUG-018` is a real helper-contract defect, but no supplied call sites were found; it is marked latent and Low.
- `BUG-025` is narrowed to callable objects and synchronous wrappers that return awaitables.

The independent check suite asserts the confirmed bad behavior and also asserts the negative evidence for the retracted/reclassified claims. It is supporting evidence, not a substitute for regression tests in the owning repositories.
