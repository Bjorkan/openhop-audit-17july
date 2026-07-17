# POSSIBLE-ENHANCEMENT-003 — Possible enhancement — centralize frontend API response normalization

[← Audit index](../README.md)

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

The bundle contains several ad-hoc variants for unwrapping Axios and backend response envelopes.

## What happens now

Components independently inspect `response`, `response.data`, or `response.data.data` and implement their own success/error messages.

## Expected behaviour / proposed direction

Add one `unwrapApiResult()` helper or Axios response adapter and one composable for mutation state.

## What needs to change

Reduces repeated code and prevents successful changes from being displayed as failures.

## Suggested code change

> **Review warning:** the linked patch is an LLM-generated implementation sketch. It is intended to show the approximate change surface, not to be applied blindly. Rebase it onto the real frontend source where compiled assets are involved, add regression tests, and review hardware/runtime implications.

[Open the suggested patch](../patches/POSSIBLE-ENHANCEMENT-003.patch)

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
