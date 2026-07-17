# BUG-002 — Configuration screens misread the standard API response envelope

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Web UI / API contract |
| Components | OpenHop Repeater Web UI |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Several configuration forms read Axios responses at the wrong level. Successful backend changes can be shown as “Unknown response”, “Failed to save”, or a terminal error even though the write completed.

## What happens now

`APIEndpoints._success()` returns `{success: true, data: payload}` and Axios returns that body as `response.data`. Some forms inspect `response.data.message` instead of `response.data.data.message`; the advert form checks `response.success` instead of `response.data.success`; the terminal similarly checks the Axios response object.

## Expected behaviour / proposed direction

Every caller should normalize the response once and then evaluate the same envelope. A shared helper should return `{ok, payload, error}`.

## What needs to change

Fix the affected radio, repeater, duty-cycle, advert-rate-limit and terminal handlers, then centralize envelope parsing to prevent recurrence.

## Reproduction / verification

The compiled bundle contains three distinct incompatible response-handling patterns; the focused static check verified all three against the backend envelope.

See [`docs/REPRODUCTION-CHECKS.md`](../docs/REPRODUCTION-CHECKS.md) and the executable check script.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-002/implementation_plan.md)


## Source references and excerpts

The affected radio, duty-cycle, advert and terminal response handlers are captured by exact bundle byte offset in [`docs/UI-SOURCE-EXCERPTS.md`](../docs/UI-SOURCE-EXCERPTS.md).

### Evidence 1: `repeater/web/api_endpoints.py` lines 268–275

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L268-L275)

```text
  268 |     def _success(self, data, **kwargs):
  269 |         result = {"success": True, "data": data}
  270 |         result.update(kwargs)
  271 |         return result
  272 | 
  273 |     def _error(self, error):
  274 |         return {"success": False, "error": str(error)}
  275 | 
```
