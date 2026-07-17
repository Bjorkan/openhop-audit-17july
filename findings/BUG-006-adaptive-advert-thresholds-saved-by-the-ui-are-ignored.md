# BUG-006 — Adaptive advert thresholds saved by the UI are ignored

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Advert rate limiting |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

The sample configuration, API and UI use `quiet_max`, `normal_max` and `busy_max`, while runtime initialization and reload read `normal`, `busy` and `congested`. The configured thresholds never take effect.

## What happens now

With the shipped keys, runtime silently falls back to 1.0, 5.0 and 15.0. The UI can display the saved values while decisions are made with different thresholds.

## Expected behaviour / proposed direction

One canonical schema and one parser must define both names and boundary semantics.

## What needs to change

Map `quiet_max → normal boundary`, `normal_max → busy boundary`, and `busy_max → congested boundary`; migrate legacy names explicitly and validate ascending order.

## Reproduction / verification

Focused check supplied 0.05/0.20/0.50 through the documented keys and observed runtime thresholds of 1.0/5.0/15.0.

See [`docs/REPRODUCTION-CHECKS.md`](../docs/REPRODUCTION-CHECKS.md) and the executable check script.

## Suggested code change

> **Review warning:** the linked patch is an LLM-generated implementation sketch. It is intended to show the approximate change surface, not to be applied blindly. Rebase it onto the real frontend source where compiled assets are involved, add regression tests, and review hardware/runtime implications.

[Open the suggested patch](../patches/BUG-006.patch)

## Source references and excerpts

The compiled UI payload containing `quiet_max`, `normal_max` and `busy_max` is captured in [`docs/UI-SOURCE-EXCERPTS.md`](../docs/UI-SOURCE-EXCERPTS.md).

### Evidence 1: `config.yaml.example` lines 100–114

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/config.yaml.example#L100-L114)

```text
  100 |   # Adaptive rate limiting based on mesh activity
  101 |   # Rate limits scale with mesh busyness: quiet mesh = lenient, busy mesh = strict
  102 |   advert_adaptive:
  103 |     # Master switch for adaptive scaling
  104 |     enabled: false
  105 |     # EWMA smoothing factor (0.0-1.0, higher = faster response)
  106 |     ewma_alpha: 0.1
  107 |     # Seconds without metrics change before tier change takes effect (hysteresis)
  108 |     hysteresis_seconds: 300
  109 |     # Tier thresholds based on adverts per minute EWMA
  110 |     thresholds:
  111 |       quiet_max: 0.05         # Below this = QUIET tier (no limiting)
  112 |       normal_max: 0.20        # Below this = NORMAL tier (1x limits)
  113 |       busy_max: 0.50          # Below this = BUSY tier (0.5x capacity)
  114 |       # Above busy_max = CONGESTED tier (0.25x capacity)
```

### Evidence 2: `repeater/web/api_endpoints.py` lines 1989–2011

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L1989-L2011)

```text
 1989 |     def update_advert_rate_limit_config(self):
 1990 |         """Update advert rate limiting configuration using ConfigManager.
 1991 | 
 1992 |         POST /api/update_advert_rate_limit_config
 1993 |         Body: {
 1994 |             "rate_limit_enabled": true,
 1995 |             "bucket_capacity": 2,
 1996 |             "refill_tokens": 1,
 1997 |             "refill_interval_seconds": 36000,
 1998 |             "min_interval_seconds": 3600,
 1999 |             "penalty_enabled": true,
 2000 |             "violation_threshold": 2,
 2001 |             "violation_decay_seconds": 43200,
 2002 |             "base_penalty_seconds": 21600,
 2003 |             "penalty_multiplier": 2.0,
 2004 |             "max_penalty_seconds": 86400,
 2005 |             "adaptive_enabled": true,
 2006 |             "ewma_alpha": 0.1,
 2007 |             "hysteresis_seconds": 300,
 2008 |             "quiet_max": 0.05,
 2009 |             "normal_max": 0.20,
 2010 |             "busy_max": 0.50
 2011 |         }
```

### Evidence 3: `repeater/web/api_endpoints.py` lines 2093–2142

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L2093-L2142)

```text
 2093 |             # Adaptive settings
 2094 |             if "adaptive_enabled" in data:
 2095 |                 adaptive_cfg["enabled"] = bool(data["adaptive_enabled"])
 2096 |                 applied.append(f"adaptive={'enabled' if adaptive_cfg['enabled'] else 'disabled'}")
 2097 | 
 2098 |             if "ewma_alpha" in data:
 2099 |                 alpha = max(0.01, min(1.0, float(data["ewma_alpha"])))
 2100 |                 adaptive_cfg["ewma_alpha"] = alpha
 2101 |                 applied.append(f"ewma_alpha={alpha}")
 2102 | 
 2103 |             if "hysteresis_seconds" in data:
 2104 |                 hyst = max(0, int(data["hysteresis_seconds"]))
 2105 |                 adaptive_cfg["hysteresis_seconds"] = hyst
 2106 |                 applied.append(f"hysteresis={hyst}s")
 2107 | 
 2108 |             # Adaptive thresholds
 2109 |             if "thresholds" not in adaptive_cfg:
 2110 |                 adaptive_cfg["thresholds"] = {}
 2111 | 
 2112 |             if "quiet_max" in data:
 2113 |                 adaptive_cfg["thresholds"]["quiet_max"] = float(data["quiet_max"])
 2114 |                 applied.append(f"quiet_max={data['quiet_max']}")
 2115 | 
 2116 |             if "normal_max" in data:
 2117 |                 adaptive_cfg["thresholds"]["normal_max"] = float(data["normal_max"])
 2118 |                 applied.append(f"normal_max={data['normal_max']}")
 2119 | 
 2120 |             if "busy_max" in data:
 2121 |                 adaptive_cfg["thresholds"]["busy_max"] = float(data["busy_max"])
 2122 |                 applied.append(f"busy_max={data['busy_max']}")
 2123 | 
 2124 |             if not applied:
 2125 |                 return self._error("No valid settings provided")
 2126 | 
 2127 |             # Save to config file and live update daemon
 2128 |             result = self.config_manager.update_and_save(
 2129 |                 updates={}, live_update=True, live_update_sections=["repeater"]
 2130 |             )
 2131 | 
 2132 |             logger.info(f"Advert rate limit config updated: {', '.join(applied)}")
 2133 | 
 2134 |             return self._success(
 2135 |                 {
 2136 |                     "applied": applied,
 2137 |                     "persisted": result.get("saved", False),
 2138 |                     "live_update": result.get("live_updated", False),
 2139 |                     "restart_required": False,
 2140 |                     "message": "Advert rate limit settings applied immediately.",
 2141 |                 }
 2142 |             )
```

### Evidence 4: `repeater/handler_helpers/advert.py` lines 63–87

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

### Evidence 5: `repeater/handler_helpers/advert.py` lines 283–295

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/advert.py#L283-L295)

```text
  283 |     def _calculate_target_tier(self) -> MeshActivityTier:
  284 |         """Determine target tier based on current EWMA metrics."""
  285 |         # Combined activity score (adverts + packets weighted)
  286 |         activity = self._adverts_ewma + (self._packets_ewma * 0.1)
  287 | 
  288 |         if activity >= self._threshold_congested:
  289 |             return MeshActivityTier.CONGESTED
  290 |         elif activity >= self._threshold_busy:
  291 |             return MeshActivityTier.BUSY
  292 |         elif activity >= self._threshold_normal:
  293 |             return MeshActivityTier.NORMAL
  294 |         else:
  295 |             return MeshActivityTier.QUIET
```

### Evidence 6: `repeater/handler_helpers/advert.py` lines 663–689

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
