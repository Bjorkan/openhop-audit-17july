# Reverification report — 17 July 2026

The prior audit, its reproduction scripts and its implementation plans were treated as untrusted. Claims were re-derived from fresh source extractions and checked against reachable runtime paths, explicit documentation and independent executable tests.

## Independent update — 18 July 2026

The supplied audit was again treated as untrusted and checked only against the newly supplied Core and Repeater ZIPs. All **46** pre-existing active defects and all **18** active possible enhancements were retained. Fourteen source-evidence ranges were corrected after Core line movement or nearby code changes. All **64** existing plans were reviewed; `BUG-049` and its plan were added after three new checks passed.

The current Core suite passes **1,331/1,331** tests. The Repeater suite runs **1,222** tests against that Core snapshot and reports **1,221 passed, 1 failed** because the Core `NodePrefs.airtime_factor` default is now `1.0` while one Repeater test still expects `0`. That source-snapshot mismatch is documented but is not classified as a runtime bug without independent evidence of the intended external default.

## Defect claims

| Original ID | Verdict | Reverified conclusion |
|---|---|---|
| BUG-001 | **Confirmed** | Backend budget utilization and compiled UI double-normalization both reproduce. |
| BUG-002 | **Retracted** | False positive: the shared API wrapper returns the backend envelope and the views unwrap it consistently. |
| BUG-003 | **Confirmed** | The enforced limit is cached in `AirtimeManager` and duty live reload does not refresh it. |
| BUG-004 | **Confirmed** | Live radio apply leaves cached airtime modulation parameters unchanged. |
| BUG-005 | **Confirmed** | The SX1262 `configure_radio` live branch omits the separate transmit-power setter. |
| BUG-006 | **Confirmed** | Writer and reader use incompatible adaptive-threshold key names. |
| BUG-007 | **Confirmed** | The endpoint reports top-level success and immediate application even when save/live-apply results are false. |
| BUG-008 | **Confirmed** | The endpoint promises full backup restore, but full export contains sections excluded by the import allowlist. |
| BUG-009 | **Confirmed** | Configuration import ignores persistence failures in its top-level success result. |
| BUG-010 | **Confirmed** | Sequential mutation occurs before later validation failure and is not rolled back. |
| BUG-011 | **Confirmed; wording corrected** | Realtime clock changes invalidate elapsed-time windows: forward jumps can expire them; backward jumps can extend them. |
| BUG-012 | **Confirmed** | Quick endpoints mutate memory only while compiled terminal code forces the result to `persisted=true`. |
| BUG-013 | **Confirmed; wording corrected** | PATH/protocol-response dedupe commits even when no bridge authenticates or every bridge raises. |
| BUG-014 | **Confirmed** | An exception from one companion bridge prevents a colliding local identity from being tried. |
| BUG-015 | **Confirmed** | `skip_mqtt` is propagated into publication code but ignored. |
| BUG-016 | **Confirmed** | The raw duplicate path omits the configured cap applied by the normal receive path. |
| BUG-017 | **Confirmed; High→Medium** | Missing `cache_ttl` and explicit values below the startup minimum are interpreted differently at reload. |
| BUG-018 | **Confirmed latent defect; Medium→Low** | The helper violates its dotted-path contract, but no supplied call sites were found. |
| BUG-019 | **Confirmed** | OpenAPI documents fields different from those accepted by the implemented duty endpoint. |
| BUG-020 | **Confirmed** | Install can overlap a check and stale check completion can report idle while install is active. |
| BUG-021 | **Confirmed** | A check result has no channel/job ownership token and can be attached to a newly selected channel. |
| BUG-022 | **Confirmed** | Update-channel persistence failure is swallowed while the endpoint reports success. |
| BUG-023 | **Confirmed** | Runtime password changes before persistence and is not rolled back on failure. |
| BUG-024 | **Confirmed** | An enhanced callback that raises is retried with another signature, causing a second invocation. |
| BUG-025 | **Confirmed; examples narrowed** | Sync wrappers and callable objects returning awaitables are not awaited. |
| BUG-026 | **Reclassified** | The lossy behavior exists, but destructive pop and queue-full shedding are explicitly documented semantics; stronger delivery belongs in PE-018. |
| BUG-027 | **Confirmed** | An interleaving push during asynchronous persistence lets `pop_last()` remove the newer entry. |

## Possible enhancements

| Original ID | Verdict | Reverified conclusion |
|---|---|---|
| POSSIBLE-ENHANCEMENT-001 | **Retained** | Retained; now includes OpenAPI generation formerly duplicated by PE-019. |
| POSSIBLE-ENHANCEMENT-002 | **Retained** | Retained; repeated transaction orchestration and inconsistent failure handling are present. |
| POSSIBLE-ENHANCEMENT-003 | **Retained** | Retained with corrected rationale; current envelope access is correct, so this is optional type-safety work. |
| POSSIBLE-ENHANCEMENT-004 | **Retained** | Retained; airtime fields are copied and renamed across producer/consumer layers. |
| POSSIBLE-ENHANCEMENT-005 | **Retained** | Retained; radio live apply is introspection-driven and capability logic is duplicated. |
| POSSIBLE-ENHANCEMENT-006 | **Retained** | Retained; relative timers directly depend on mutable wall clock. |
| POSSIBLE-ENHANCEMENT-007 | **Retained** | Retained; `api_endpoints.py` spans unrelated domains and exceeds 7,000 lines. |
| POSSIBLE-ENHANCEMENT-008 | **Retained** | Retained; configuration writes directly to the target path without atomic replacement/last-known-good recovery. |
| POSSIBLE-ENHANCEMENT-009 | **Retained** | Retained; advert-limiter parsing is duplicated between startup and reload. |
| POSSIBLE-ENHANCEMENT-010 | **Retained** | Retained; only compiled frontend assets are supplied, without source maps or reproducible build metadata. |
| POSSIBLE-ENHANCEMENT-011 | **Retained** | Retained; companion delivery outcome and dedupe commit orchestration is repeated. |
| POSSIBLE-ENHANCEMENT-012 | **Retained** | Retained; duplicate grouping logic is split across normal and raw paths. |
| POSSIBLE-ENHANCEMENT-013 | **Retained** | Retained; startup/reload runtime parsing differs and has already drifted. |
| POSSIBLE-ENHANCEMENT-014 | **Retained** | Retained; sink policy is encoded by narrow booleans with implicit combinations. |
| POSSIBLE-ENHANCEMENT-015 | **Retained** | Retained; callback invocation logic is duplicated and inconsistent. |
| POSSIBLE-ENHANCEMENT-016 | **Retained** | Retained; updater operations lack an ownership/job token. |
| POSSIBLE-ENHANCEMENT-017 | **Retained** | Retained; storage executor submission is unbounded and lacks queue metrics. |
| POSSIBLE-ENHANCEMENT-018 | **Retained** | Retained; now includes documented destructive-pop/queue-shedding limitations and stable queue identities. |
| POSSIBLE-ENHANCEMENT-019 | **Merged** | Merged into PE-001 as duplicate typed-contract/OpenAPI scope. |
| POSSIBLE-ENHANCEMENT-020 | **Merged** | Merged into BUG-027 and PE-018 as remediation/prerequisite rather than a separate work item. |

## Verification method

- Fresh extraction of both source ZIPs.
- Complete Core and Repeater test suites rerun.
- 28 independent executable checks, including negative checks for the retracted and reclassified claims.
- 25 active-falsification checks covering every active baseline finding.
- 20 factual-premise checks for possible enhancements.
- Baseline: 4,371 quoted source lines compared byte-for-byte with the fresh source trees; zero mismatches.
- External-entry-to-runtime tracing for configuration, API, callback, queue and updater paths.
- Source/test path and finding-link validation for all 65 active implementation plans.
- Relative Markdown link validation, SHA-256 manifest validation and ZIP integrity testing.

## Limitations

- Passing project tests do not prove absence of defects; most confirmed cases were outside existing regression coverage.
- The supplied frontend contains generated/minified assets only. Source-level UI fixes must be made in the real frontend source and rebuilt.
- No `.git` metadata was supplied, so branch history, intent discussions and later upstream fixes cannot be inferred.
- A confirmed finding is confirmed only against the supplied snapshots, not every later or earlier revision.

## Triple-verified continuation

The continuation now contains 22 reports, BUG-028 through BUG-049. Each passed three independent checks; see [`TRIPLE-VERIFICATION-REPORT.md`](TRIPLE-VERIFICATION-REPORT.md). The 46 findings active before this update retained their final classifications and severities. The 25 baseline findings are now explicitly recorded as three-method verified in [`BASELINE-TRIPLE-VERIFICATION.md`](BASELINE-TRIPLE-VERIFICATION.md).
