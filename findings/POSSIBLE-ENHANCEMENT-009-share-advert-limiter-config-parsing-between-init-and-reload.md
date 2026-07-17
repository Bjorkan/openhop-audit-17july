# POSSIBLE-ENHANCEMENT-009 — Possible enhancement — share advert-limiter config parsing between initialization and reload

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Code reuse |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

AdvertHelper repeats almost the same configuration parsing in `__init__` and `reload_config`.

## What happens now

The blocks independently parse adaptive, rate-limit, penalty and dedupe settings; this duplication enabled the threshold-key drift to exist in two places.

## Expected behaviour / proposed direction

Extract `_parse_limiter_config()` returning a validated snapshot and use it for both initialization and reload.

## What needs to change

Cuts repeated code, centralizes migration/default behavior and simplifies tests.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-009/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/handler_helpers/advert.py` lines 63–87

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/advert.py#L63-L87)

```text
   63 |         repeater_cfg = self.config.get("repeater", {})
   64 | 
   65 |         # --- Adaptive mode config ---
   66 |         adaptive_cfg = repeater_cfg.get("advert_adaptive", {})
   67 |         self._adaptive_enabled = bool(adaptive_cfg.get("enabled", False))
   68 |         self._ewma_alpha = max(0.01, min(1.0, float(adaptive_cfg.get("ewma_alpha", 0.1))))
   69 |         self._tier_hysteresis_seconds = max(
   70 |             0.0, float(adaptive_cfg.get("hysteresis_seconds", 300.0))
   71 |         )
   72 | 
   73 |         # Tier thresholds (packets per minute)
   74 |         thresholds = adaptive_cfg.get("thresholds", {})
   75 |         self._threshold_normal = float(thresholds.get("normal", 1.0))
   76 |         self._threshold_busy = float(thresholds.get("busy", 5.0))
   77 |         self._threshold_congested = float(thresholds.get("congested", 15.0))
   78 | 
   79 |         # --- Base rate limit config (scaled by tier) ---
   80 |         rate_cfg = repeater_cfg.get("advert_rate_limit", {})
   81 |         self._rate_limit_enabled = bool(rate_cfg.get("enabled", False))
   82 |         self._base_bucket_capacity = max(1.0, float(rate_cfg.get("bucket_capacity", 2)))
   83 |         self._base_refill_tokens = max(0.1, float(rate_cfg.get("refill_tokens", 1.0)))
   84 |         self._base_refill_interval = max(
   85 |             1.0, float(rate_cfg.get("refill_interval_seconds", 36000.0))
   86 |         )
   87 |         self._base_min_interval = max(0.0, float(rate_cfg.get("min_interval_seconds", 3600.0)))
```

### Evidence 2: `repeater/handler_helpers/advert.py` lines 663–689

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/advert.py#L663-L689)

```text
  663 |     def reload_config(self) -> None:
  664 |         """Reload rate limiting configuration from self.config (called after live config updates)."""
  665 |         try:
  666 |             repeater_cfg = self.config.get("repeater", {})
  667 | 
  668 |             # Adaptive mode config
  669 |             adaptive_cfg = repeater_cfg.get("advert_adaptive", {})
  670 |             self._adaptive_enabled = bool(adaptive_cfg.get("enabled", False))
  671 |             self._ewma_alpha = max(0.01, min(1.0, float(adaptive_cfg.get("ewma_alpha", 0.1))))
  672 |             self._tier_hysteresis_seconds = max(
  673 |                 0.0, float(adaptive_cfg.get("hysteresis_seconds", 300.0))
  674 |             )
  675 | 
  676 |             thresholds = adaptive_cfg.get("thresholds", {})
  677 |             self._threshold_normal = float(thresholds.get("normal", 1.0))
  678 |             self._threshold_busy = float(thresholds.get("busy", 5.0))
  679 |             self._threshold_congested = float(thresholds.get("congested", 15.0))
  680 | 
  681 |             # Base rate limit config
  682 |             rate_cfg = repeater_cfg.get("advert_rate_limit", {})
  683 |             self._rate_limit_enabled = bool(rate_cfg.get("enabled", False))
  684 |             self._base_bucket_capacity = max(1.0, float(rate_cfg.get("bucket_capacity", 2)))
  685 |             self._base_refill_tokens = max(0.1, float(rate_cfg.get("refill_tokens", 1.0)))
  686 |             self._base_refill_interval = max(
  687 |                 1.0, float(rate_cfg.get("refill_interval_seconds", 36000.0))
  688 |             )
  689 |             self._base_min_interval = max(0.0, float(rate_cfg.get("min_interval_seconds", 3600.0)))
```
