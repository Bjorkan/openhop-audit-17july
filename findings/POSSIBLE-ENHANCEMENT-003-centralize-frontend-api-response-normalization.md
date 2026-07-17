# POSSIBLE-ENHANCEMENT-003 — Possible enhancement — centralize frontend API response normalization

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Web UI architecture |
| Components | OpenHop Repeater Web UI |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

The bundle contains several direct access patterns for the backend envelope. Reverification found the examined patterns semantically correct; centralization is a type-safety and maintainability proposal, not evidence of a response-handling defect.

## What happens now

Components independently inspect `response`, `response.data`, or `response.data.data` and implement their own success/error messages.

## Expected behaviour / proposed direction

Add one `unwrapApiResult()` helper or Axios response adapter and one composable for mutation state.

## What needs to change

Reduces repeated code and prevents successful changes from being displayed as failures.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-003/implementation_plan.md)


## Source references and excerpts

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
