# POSSIBLE-ENHANCEMENT-019 — Possible enhancement — generate OpenAPI request schemas from the same models used by endpoints

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | API maintainability |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

The handwritten OpenAPI document and handwritten endpoint parsing can drift independently.

## What happens now

The duty-cycle schema already describes an obsolete timing model while runtime implements a percentage model.

## Expected behaviour / proposed direction

Define typed request/response models once and generate or validate OpenAPI from them during CI.

## What needs to change

Prevents field-name drift, enables generated clients and centralizes validation constraints/examples.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-019/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/web/openapi.yaml` lines 761–794

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/openapi.yaml#L761-L794)

```text
  761 |   /update_duty_cycle_config:
  762 |     post:
  763 |       tags: [System]
  764 |       summary: Update duty cycle configuration
  765 |       description: Update detailed duty cycle timing configuration
  766 |       security:
  767 |         - BearerAuth: []
  768 |         - ApiKeyAuth: []
  769 |       requestBody:
  770 |         required: true
  771 |         content:
  772 |           application/json:
  773 |             schema:
  774 |               type: object
  775 |               properties:
  776 |                 enabled:
  777 |                   type: boolean
  778 |                 on_time:
  779 |                   type: integer
  780 |                   description: ON time in seconds
  781 |                 off_time:
  782 |                   type: integer
  783 |                   description: OFF time in seconds
  784 |             example:
  785 |               enabled: true
  786 |               on_time: 300
  787 |               off_time: 60
  788 |       responses:
  789 |         '200':
  790 |           description: Duty cycle config updated
  791 |           content:
  792 |             application/json:
  793 |               schema:
  794 |                 $ref: '#/components/schemas/SuccessResponse'
```

### Evidence 2: `repeater/web/api_endpoints.py` lines 1925–1978

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L1925-L1978)

```text
 1925 |     def update_duty_cycle_config(self):
 1926 |         self._set_cors_headers()
 1927 | 
 1928 |         if cherrypy.request.method == "OPTIONS":
 1929 |             return ""
 1930 | 
 1931 |         try:
 1932 |             self._require_post()
 1933 |             data = cherrypy.request.json or {}
 1934 | 
 1935 |             applied = []
 1936 | 
 1937 |             # Ensure config section exists
 1938 |             if "duty_cycle" not in self.config:
 1939 |                 self.config["duty_cycle"] = {}
 1940 | 
 1941 |             # Update max airtime percentage
 1942 |             if "max_airtime_percent" in data:
 1943 |                 percent = float(data["max_airtime_percent"])
 1944 |                 if percent < 0.1 or percent > 100.0:
 1945 |                     return self._error("Max airtime percent must be 0.1-100.0")
 1946 |                 # Convert percent to milliseconds per minute
 1947 |                 max_airtime_ms = int((percent / 100) * 60000)
 1948 |                 self.config["duty_cycle"]["max_airtime_per_minute"] = max_airtime_ms
 1949 |                 applied.append(f"max_airtime={percent}%")
 1950 | 
 1951 |             # Update enforcement enabled/disabled
 1952 |             if "enforcement_enabled" in data:
 1953 |                 enabled = bool(data["enforcement_enabled"])
 1954 |                 self.config["duty_cycle"]["enforcement_enabled"] = enabled
 1955 |                 applied.append(f"enforcement={'enabled' if enabled else 'disabled'}")
 1956 | 
 1957 |             if not applied:
 1958 |                 return self._error("No valid settings provided")
 1959 | 
 1960 |             # Save to config file and live update daemon
 1961 |             result = self.config_manager.update_and_save(
 1962 |                 updates={}, live_update=True, live_update_sections=["duty_cycle"]
 1963 |             )
 1964 | 
 1965 |             if not result.get("saved", False):
 1966 |                 return self._error(result.get("error", "Failed to save configuration to file"))
 1967 | 
 1968 |             logger.info(f"Duty cycle config updated: {', '.join(applied)}")
 1969 | 
 1970 |             return self._success(
 1971 |                 {
 1972 |                     "applied": applied,
 1973 |                     "persisted": True,
 1974 |                     "live_update": result.get("live_updated", False),
 1975 |                     "restart_required": False,
 1976 |                     "message": "Duty cycle settings applied immediately.",
 1977 |                 }
 1978 |             )
```
