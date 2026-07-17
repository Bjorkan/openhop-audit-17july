# POSSIBLE-ENHANCEMENT-002 — Possible enhancement — introduce a transactional configuration update service

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Configuration architecture |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Endpoint methods repeat “ensure section → mutate → save → live reload → craft response,” with inconsistent failure handling.

## What happens now

Each endpoint directly edits the shared dictionary and interprets `ConfigManager` results differently.

## Expected behaviour / proposed direction

Provide a transaction API that validates a candidate snapshot, atomically persists it, applies runtime changes, and rolls back or reports restart requirements.

## What needs to change

Removes duplicate code and directly prevents partial mutation, false-success and persistence inconsistencies.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-002/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/config_manager.py` lines 359–417

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config_manager.py#L359-L417)

```text
  359 |     def update_and_save(
  360 |         self,
  361 |         updates: Dict[str, Any],
  362 |         live_update: bool = True,
  363 |         live_update_sections: Optional[List[str]] = None,
  364 |     ) -> Dict[str, Any]:
  365 |         """
  366 |         Apply updates to config, save to file, and optionally live update daemon.
  367 | 
  368 |         This is the main method that should be used by both mesh_cli and api_endpoints.
  369 | 
  370 |         Args:
  371 |             updates: Dictionary of config updates in nested format.
  372 |                     Example: {"repeater": {"node_name": "NewName"}, "delays": {"tx_delay_factor": 1.5}}
  373 |             live_update: Whether to apply changes to running daemon immediately
  374 |             live_update_sections: Specific sections to live update. If None, auto-detects from updates.
  375 | 
  376 |         Returns:
  377 |             Dict with keys:
  378 |                 - success: bool - Whether operation succeeded
  379 |                 - saved: bool - Whether config was saved to file
  380 |                 - live_updated: bool - Whether daemon was live updated
  381 |                 - error: str (optional) - Error message if failed
  382 |         """
  383 |         result: Dict[str, Any] = {"success": False, "saved": False, "live_updated": False}
  384 | 
  385 |         try:
  386 |             # Apply updates to config
  387 |             for section, values in updates.items():
  388 |                 if section not in self.config:
  389 |                     self.config[section] = {}
  390 | 
  391 |                 if isinstance(values, dict):
  392 |                     self.config[section].update(values)
  393 |                 else:
  394 |                     self.config[section] = values
  395 | 
  396 |             # Save to file
  397 |             result["saved"] = self.save_to_file()
  398 | 
  399 |             if not result["saved"]:
  400 |                 result["error"] = "Failed to save config to file"
  401 |                 return result
  402 | 
  403 |             # Live update daemon if requested
  404 |             if live_update:
  405 |                 # Auto-detect sections if not specified
  406 |                 if live_update_sections is None:
  407 |                     live_update_sections = list(updates.keys())
  408 | 
  409 |                 result["live_updated"] = self.live_update_daemon(live_update_sections)
  410 | 
  411 |             result["success"] = result["saved"]
  412 |             return result
  413 | 
  414 |         except Exception as e:
  415 |             logger.error(f"Error in update_and_save: {e}", exc_info=True)
  416 |             result["error"] = str(e)
  417 |             return result
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
