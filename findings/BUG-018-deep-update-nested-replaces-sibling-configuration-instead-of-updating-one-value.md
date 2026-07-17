# BUG-018 — `update_nested()` replaces sibling configuration instead of updating one deep value

[← Audit index](../README.md)

> Reverification verdict: **Confirmed against the supplied snapshot.**

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Low** |
| Confidence | **Confirmed** |
| Area | Configuration helper semantics |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

The convenience helper claims to update a dotted path, but paths deeper than one level are passed into a shallow section update and replace the entire intermediate mapping.

## What happens now

For `repeater.security.admin_password`, `update_nested()` constructs `{repeater: {security: {admin_password: ...}}}`. `update_and_save()` then performs `config["repeater"].update(...)`, replacing all of `security`; JWT secrets, guest credentials or other sibling keys disappear.

## Expected behaviour / proposed direction

A dotted-path update must modify exactly the named leaf and preserve unrelated siblings.

## What needs to change

Traverse a copied config to the target leaf, assign there, and commit transactionally. Alternatively make `update_and_save()` perform a documented recursive merge, with explicit replacement markers for callers that need replacement.

## Reproduction / verification

The deeper focused check updated only `repeater.security.admin_password`; the resulting security mapping contained only that key.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-018/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/config_manager.py` lines 385–417

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config_manager.py#L385-L417)

```text
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

### Evidence 2: `repeater/config_manager.py` lines 419–461

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config_manager.py#L419-L461)

```text
  419 |     def update_nested(self, path: str, value: Any, live_update: bool = True) -> Dict[str, Any]:
  420 |         """
  421 |         Update a nested config value using dot notation.
  422 | 
  423 |         Convenience method for simple updates like "repeater.node_name" = "NewName"
  424 | 
  425 |         Args:
  426 |             path: Dot-separated path to config value (e.g., "repeater.node_name")
  427 |             value: Value to set
  428 |             live_update: Whether to apply changes to running daemon
  429 | 
  430 |         Returns:
  431 |             Result dict from update_and_save
  432 |         """
  433 |         parts = path.split(".")
  434 | 
  435 |         if len(parts) == 1:
  436 |             # Top-level key
  437 |             updates = {parts[0]: value}
  438 |         elif len(parts) == 2:
  439 |             # Nested one level (most common case)
  440 |             updates = {parts[0]: {parts[1]: value}}
  441 |         else:
  442 |             # Build nested dict for deeper paths
  443 |             updates = {}
  444 |             current = updates
  445 |             for i, part in enumerate(parts[:-1]):
  446 |                 if i == 0:
  447 |                     current[part] = {}
  448 |                     current = current[part]
  449 |                 else:
  450 |                     current[part] = {}
  451 |                     current = current[part]
  452 |             current[parts[-1]] = value
  453 | 
  454 |         # Determine which section to live update
  455 |         section = parts[0]
  456 | 
  457 |         return self.update_and_save(
  458 |             updates=updates,
  459 |             live_update=live_update,
  460 |             live_update_sections=[section] if live_update else None,
  461 |         )
```
