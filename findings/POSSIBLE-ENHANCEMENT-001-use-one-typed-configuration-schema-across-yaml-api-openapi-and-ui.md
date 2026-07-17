# POSSIBLE-ENHANCEMENT-001 — Possible enhancement — use one typed configuration schema across YAML, API, OpenAPI and UI

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Configuration architecture |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Configuration names, defaults, ranges and units are currently repeated in several layers and have already drifted. OpenAPI request schemas should be generated from the same typed models rather than maintained as a separate handwritten contract.

## What happens now

Defaults live in `config.py`/`config.yaml.example`; endpoint validation is handwritten in a 7,000+ line controller; OpenAPI and compiled UI duplicate the same values.

## Expected behaviour / proposed direction

Create typed section models (for example dataclasses or Pydantic), generate JSON Schema/OpenAPI fragments, and let frontend forms consume the same contract.

## What needs to change

Eliminates key/range drift, provides uniform coercion and error messages, and makes export/import coverage enumerable.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-001/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/web/api_endpoints.py` lines 3962–4020

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L3962-L4020)

```text
 3962 |         try:
 3963 |             self._require_post()
 3964 |             data = cherrypy.request.json or {}
 3965 | 
 3966 |             applied = []
 3967 | 
 3968 |             # Ensure config sections exist
 3969 |             if "radio" not in self.config:
 3970 |                 self.config["radio"] = {}
 3971 |             if "delays" not in self.config:
 3972 |                 self.config["delays"] = {}
 3973 |             if "repeater" not in self.config:
 3974 |                 self.config["repeater"] = {}
 3975 |             if "mesh" not in self.config:
 3976 |                 self.config["mesh"] = {}
 3977 | 
 3978 |             # Update TX power (up to 30 dBm for high-power radios)
 3979 |             if "tx_power" in data:
 3980 |                 power = int(data["tx_power"])
 3981 |                 if power < 2 or power > 30:
 3982 |                     return self._error("TX power must be 2-30 dBm")
 3983 |                 self.config["radio"]["tx_power"] = power
 3984 |                 applied.append(f"power={power}dBm")
 3985 | 
 3986 |             # Update frequency (in Hz)
 3987 |             if "frequency" in data:
 3988 |                 freq = float(data["frequency"])
 3989 |                 if freq < 100_000_000 or freq > 1_000_000_000:
 3990 |                     return self._error("Frequency must be 100-1000 MHz")
 3991 |                 self.config["radio"]["frequency"] = freq
 3992 |                 applied.append(f"freq={freq / 1_000_000:.3f}MHz")
 3993 | 
 3994 |             # Update bandwidth (in Hz)
 3995 |             if "bandwidth" in data:
 3996 |                 bw = int(float(data["bandwidth"]))
 3997 |                 valid_bw = [7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000, 500000]
 3998 |                 if bw not in valid_bw:
 3999 |                     return self._error(
 4000 |                         f"Bandwidth must be one of {[b / 1000 for b in valid_bw]} kHz"
 4001 |                     )
 4002 |                 self.config["radio"]["bandwidth"] = bw
 4003 |                 applied.append(f"bw={bw / 1000}kHz")
 4004 | 
 4005 |             # Update spreading factor
 4006 |             if "spreading_factor" in data:
 4007 |                 sf = int(data["spreading_factor"])
 4008 |                 if sf < 5 or sf > 12:
 4009 |                     return self._error("Spreading factor must be 5-12")
 4010 |                 self.config["radio"]["spreading_factor"] = sf
 4011 |                 applied.append(f"sf={sf}")
 4012 | 
 4013 |             # Update coding rate
 4014 |             if "coding_rate" in data:
 4015 |                 cr = int(data["coding_rate"])
 4016 |                 if cr < 5 or cr > 8:
 4017 |                     return self._error("Coding rate must be 5-8 (for 4/5 to 4/8)")
 4018 |                 self.config["radio"]["coding_rate"] = cr
 4019 |                 applied.append(f"cr=4/{cr}")
 4020 | 
```

### Evidence 2: `config.yaml.example` lines 100–114

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

### Evidence 3: `repeater/web/api_endpoints.py` lines 1989–2011

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
