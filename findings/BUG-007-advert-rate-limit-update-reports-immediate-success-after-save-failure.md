# BUG-007 — Advert-rate-limit update reports immediate success after save or live-update failure

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Configuration persistence / UI contract |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

The endpoint always returns a successful envelope and says settings were applied immediately, even when `ConfigManager` reports that the file was not saved or runtime reload failed.

## What happens now

The response exposes `persisted: false` and `live_update: false` inside a `success: true` result, while hard-coding `restart_required: false` and an immediate-success message.

## Expected behaviour / proposed direction

Persistence failure must be an API failure. A successful save with failed live reload must clearly require restart.

## What needs to change

Use the same result handling as the duty-cycle and radio endpoints, including rollback or a restart-required response.

## Reproduction / verification

Focused check injected `saved=false`, `live_updated=false`, `error="disk full"`; the endpoint still returned `success=true` and “applied immediately.”

See [`docs/REPRODUCTION-CHECKS.md`](../docs/REPRODUCTION-CHECKS.md) and the executable check script.

## Suggested code change

> **Review warning:** the linked patch is an LLM-generated implementation sketch. It is intended to show the approximate change surface, not to be applied blindly. Rebase it onto the real frontend source where compiled assets are involved, add regression tests, and review hardware/runtime implications.

[Open the suggested patch](../patches/BUG-007.patch)

## Source references and excerpts

### Evidence 1: `repeater/web/api_endpoints.py` lines 2093–2142

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

### Evidence 2: `repeater/config_manager.py` lines 359–417

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
