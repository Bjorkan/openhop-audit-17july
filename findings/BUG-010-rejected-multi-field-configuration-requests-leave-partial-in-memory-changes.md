# BUG-010 — Rejected multi-field configuration requests leave partial in-memory changes

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. The finding survived an independent static runtime trace, executable reproduction and active falsification pass on 18 July 2026.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Triple-verified** |
| Area | Configuration transactions |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Independent recheck | 2026-07-18 |
| Status | Open in supplied snapshot |

## TL;DR

Endpoints mutate the shared runtime configuration field-by-field before validating the complete request. A later invalid field returns an error but earlier fields remain changed in memory.

## What happens now

For example, `update_radio_config` writes TX power before validating bandwidth. A request containing valid power and invalid bandwidth is rejected, yet the shared config retains the new power. An unrelated later save can persist that hidden partial change.

## Expected behaviour / proposed direction

A failed request must leave both runtime and persisted configuration unchanged.

## What needs to change

Validate into a deep copy or typed request model, then commit the full change only after all validation passes. Roll back if save or live apply fails.

## Reproduction / verification

Focused check sent `{tx_power: 10, bandwidth: 12345}`. The response was failure, while `config["radio"]["tx_power"]` had already changed from 2 to 10.

See [`docs/REVERIFICATION-CHECKS.md`](../docs/REVERIFICATION-CHECKS.md) and the executable check script.

## Triple verification

| Method | Result | Record |
|---|---|---|
| Static runtime trace | **Passed** | The complete reachable path and exact quoted source excerpts in this report were revalidated byte-for-byte against the supplied source trees. |
| Executable reproduction | **Passed** | `test_bug_010_confirmed_invalid_later_field_leaves_earlier_runtime_mutation` in [`REVERIFICATION-CHECKS.py`](../docs/REVERIFICATION-CHECKS.py). |
| Active falsification | **Passed** | Earlier shared-state mutation occurs before later validation failure, with no staged copy or rollback. See [`BASELINE-FALSIFICATION-CHECKS.py`](../docs/BASELINE-FALSIFICATION-CHECKS.py). |

The consolidated baseline matrix and captured results are in [`BASELINE-TRIPLE-VERIFICATION.md`](../docs/BASELINE-TRIPLE-VERIFICATION.md).

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-010/implementation_plan.md)


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
