# Verification notes

## Method

- Unpacked the supplied Core, Repeater and prior-audit archives independently.
- Used the prior audit only to reproduce its directory/report organisation.
- Indexed all `88` Core and `68` Repeater Python source files.
- Traced configuration values from YAML/defaults through API mutation, runtime reload, telemetry and compiled UI consumers.
- Searched relative-time logic in relation to the built-in GPS system-clock setter.
- Inspected hardware wrapper capabilities used by Repeater live configuration.
- Ran the complete supplied test suites and first-pass focused reproductions.
- Performed a second manual pass over companion routing, queue ownership, callback invocation, updater state transitions, nested config mutation and external publication policy.
- Ran 15 additional executable reproductions against the unchanged source snapshots.

## Test results

- Core: 1,272 collected and passed.
- Repeater: 1,222 collected and passed.
- Python bytecode compilation: passed for both source trees.
- OpenAPI contract script: passed.
- Focused audit reproductions: 27 passed (12 first-pass + 15 deeper checks).

Passing existing tests does not invalidate the findings: several tests assert the current contradictory response shape or do not connect the UI/backend/runtime layers in one scenario.

## Frontend limitation

The archive includes compiled/minified JavaScript only. No `.vue`, `.ts`, `.tsx` or source-map files corresponding to the application source were found. UI evidence is therefore recorded by exact compiled asset filename and byte offset. Source-level UI patches are implementation sketches rather than directly applicable diffs.

## Confidence

Every bug report is based on a direct code path and, where practical, an executable focused reproduction. Possible enhancements are deliberately separated from bug counts.

## Deep-review note

The complete project suites were not rerun after generating this documentation because the audited source trees were not modified. Their captured first-pass results remain applicable. The 15 new checks import and execute the same supplied source snapshots and are included with captured output.
