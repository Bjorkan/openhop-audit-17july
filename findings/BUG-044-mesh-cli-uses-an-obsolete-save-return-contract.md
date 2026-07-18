# BUG-044 — Mesh CLI uses an obsolete configuration-save return contract

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | Mesh CLI / persistence contract |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## TL;DR

Production `ConfigManager.save_to_file()` returns one boolean, while Mesh CLI tuple-unpacks it at 23 call sites. Commands can successfully write the file and then throw `cannot unpack non-iterable bool object`, skip live application, and report an error despite partial success. Existing tests mock the obsolete tuple shape.

## Expected behavior

All callers and tests must use one typed save result, with persistence and live-application stages reported consistently.

## Required direction

1. Replace the boolean with a typed `SaveResult` or update every caller to the current boolean contract.
2. Refactor the repeated save/live/reply sequence into one shared Mesh CLI helper.
3. Correct test doubles to use the production signature and add partial-success regression tests.

## Triple verification

| Method | Check | Result | Observation |
|---:|---|---|---|
| 1 | Static signature/callsites | **Passed** | Production returns bool; Mesh CLI has 23 tuple-unpack sites. |
| 2 | Real public command | **Passed** | The file is written, then the command returns a Python error and skips live update. |
| 3 | Test-double countercheck | **Passed** | Tests mock a tuple, explaining why the suite does not catch production behavior. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition.

## Implementation plan

See [`implementation-plans/BUG-044/implementation_plan.md`](../implementation-plans/BUG-044/implementation_plan.md).

## Source evidence

### Evidence 1: `repeater/config_manager.py` lines 227–262

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config_manager.py#L227-L262)

```text
  227 |     def save_to_file(self) -> bool:
  228 |         """
  229 |         Save current config to YAML file.
  230 | 
  231 |         Returns:
  232 |             True if successful, False otherwise
  233 |         """
  234 |         try:
  235 |             os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
  236 |             with open(self.config_path, "w") as f:
  237 |                 # Use safe_dump with explicit width to prevent line wrapping
  238 |                 # Setting width to a very large number prevents truncation of long strings like identity keys
  239 |                 yaml.safe_dump(
  240 |                     self.config,
  241 |                     f,
  242 |                     default_flow_style=False,
  243 |                     indent=2,
  244 |                     width=1000000,  # Very large width to prevent any line wrapping
  245 |                     sort_keys=False,
  246 |                     allow_unicode=True,
  247 |                 )
  248 |             logger.info(f"Configuration saved to {self.config_path}")
  249 |             return True
  250 |         except Exception as e:
  251 |             logger.error(f"Failed to save config to {self.config_path}: {e}", exc_info=True)
  252 |             return False
  253 | 
  254 |     def live_update_daemon(self, sections: Optional[List[str]] = None) -> bool:
  255 |         """
  256 |         Apply configuration changes to the running daemon's in-memory config.
  257 | 
  258 |         Args:
  259 |             sections: List of config sections to update (e.g., ['repeater', 'delays']).
  260 |                      If None, updates all common sections.
  261 | 
  262 |         Returns:
```
### Evidence 2: `repeater/handler_helpers/mesh_cli.py` lines 450–470

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/mesh_cli.py#L450-L470)

```text
  450 |         # Update security config
  451 |         if "security" not in self.config:
  452 |             self.config["security"] = {}
  453 | 
  454 |         self.config["security"]["password"] = new_password
  455 | 
  456 |         # Save config and live update
  457 |         try:
  458 |             saved, err = self.config_manager.save_to_file()
  459 |             if not saved:
  460 |                 logger.error(f"Failed to save password: {err}")
  461 |                 return f"Error: Failed to save config: {err}"
  462 |             self.config_manager.live_update_daemon(["security"])
  463 |             return f"password now: {new_password}"
  464 |         except Exception as e:
  465 |             logger.error(f"Failed to save password: {e}")
  466 |             return "Error: Failed to save password"
  467 | 
  468 |     def _cmd_clear_stats(self) -> str:
  469 |         """Clear statistics."""
  470 |         # TODO: Implement stats clearing
```
### Evidence 3: `tests/test_handler_helpers_mesh_cli.py` lines 38–49

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/tests/test_handler_helpers_mesh_cli.py#L38-L49)

```text
   38 | 
   39 | def _cfg_mgr(save_ok=True, err=None):
   40 |     return SimpleNamespace(
   41 |         save_to_file=MagicMock(return_value=(save_ok, err)),
   42 |         live_update_daemon=MagicMock(),
   43 |     )
   44 | 
   45 | 
   46 | def test_handle_command_admin_and_prefix_behavior():
   47 |     cli = MeshCLI("/tmp/cfg.yaml", _base_config(), _cfg_mgr())
   48 | 
   49 |     assert cli.handle_command(b"a", "help", is_admin=False) == "Error: Admin permission required"
```

