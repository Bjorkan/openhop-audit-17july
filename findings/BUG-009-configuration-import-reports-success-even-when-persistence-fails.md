# BUG-009 — Configuration import reports success even when persistence fails

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Backup and restore |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Configuration import ignores the result of `update_and_save`, writes the file a second time, and returns `success: true` even when both persistence attempts fail.

## What happens now

The UI can tell the operator that a restore completed while the process only holds transient in-memory changes. A restart then loses the imported configuration.

## Expected behaviour / proposed direction

Import should perform one validated transaction and return success only when persistence succeeds. Live-update failures should be distinguished from disk failures.

## What needs to change

Capture the `update_and_save` result, remove the duplicate save, rollback in-memory changes on failure, and expose `live_updated`/`restart_required` accurately.

## Reproduction / verification

Focused check forced both save paths to fail; the endpoint returned `success=true`, `saved=false`, and “Imported 1 config section(s).”

See [`docs/REPRODUCTION-CHECKS.md`](../docs/REPRODUCTION-CHECKS.md) and the executable check script.

## Suggested code change

> **Review warning:** the linked patch is an LLM-generated implementation sketch. It is intended to show the approximate change surface, not to be applied blindly. Rebase it onto the real frontend source where compiled assets are involved, add regression tests, and review hardware/runtime implications.

[Open the suggested patch](../patches/BUG-009.patch)

## Source references and excerpts

### Evidence 1: `repeater/web/api_endpoints.py` lines 7392–7413

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L7392-L7413)

```text
 7392 |                 updated_sections.append(section)
 7393 | 
 7394 |             if not updated_sections:
 7395 |                 return self._error("No valid configuration sections found in import")
 7396 | 
 7397 |             # Persist and live-reload
 7398 |             self.config_manager.update_and_save(
 7399 |                 updates={},  # Already applied above
 7400 |                 live_update=True,
 7401 |                 live_update_sections=updated_sections,
 7402 |             )
 7403 | 
 7404 |             # Save to file (update_and_save with empty updates may not save)
 7405 |             saved = self.config_manager.save_to_file()
 7406 | 
 7407 |             return {
 7408 |                 "success": True,
 7409 |                 "message": f"Imported {len(updated_sections)} config section(s)",
 7410 |                 "sections_updated": updated_sections,
 7411 |                 "saved": saved,
 7412 |                 "restart_required": restart_required,
 7413 |             }
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
