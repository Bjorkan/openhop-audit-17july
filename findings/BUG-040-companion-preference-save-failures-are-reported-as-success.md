# BUG-040 — Companion preference save failures are reported as successful runtime changes

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🟠 **Medium** |
| Confidence | **Triple-verified** |
| Area | Companion preference persistence |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## TL;DR

`RepeaterCompanionBridge._save_prefs()` ignores the SQLite handler’s boolean result. Public setters mutate runtime preferences and return normally even when persistence fails, so a restart silently restores the old value.

## Expected behavior

Setters must report persistence failure and either roll back runtime state or explicitly expose a volatile-only result.

## Required direction

1. Make `_save_prefs()` return/raise a typed result and propagate it to all preference setters and API callers.
2. Stage the new preference, persist it, then commit runtime state; roll back on failure.
3. Log and expose the actual durable/effective state.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | Preference setter through persistence | **Passed** | The persistence method returns a boolean, but `_save_prefs` discards it and the setter mutates runtime state. |
| Executable reproduction | Failed setter | **Passed** | An explicit false save returns normally and leaves the requested runtime value active. |
| Active falsification | Restart consistency check | **Passed** | A fresh bridge reloads the old persisted value, proving the apparent success was not durable through restart. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-040/implementation_plan.md`](../implementation-plans/BUG-040/implementation_plan.md).

## Source evidence

### Evidence 1: `repeater/companion/bridge.py` lines 97–121

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/companion/bridge.py#L97-L121)

```text
   97 |     def _save_prefs(self) -> None:
   98 |         """Persist full NodePrefs as JSON to SQLite."""
   99 |         if not self._sqlite_handler or not self._companion_hash:
  100 |             return
  101 |         try:
  102 |             prefs_dict = dataclasses.asdict(self.prefs)
  103 |             prefs_safe = _to_json_safe(prefs_dict)
  104 |             self._sqlite_handler.companion_save_prefs(str(self._companion_hash), prefs_safe)
  105 |             if self._on_prefs_saved:
  106 |                 try:
  107 |                     self._on_prefs_saved(self.prefs.node_name)
  108 |                 except Exception as e:
  109 |                     logger.warning("Failed to sync node_name to config: %s", e)
  110 |         except Exception as e:
  111 |             logger.warning("Failed to persist companion prefs: %s", e)
  112 | 
  113 |     def _load_prefs(self) -> None:
  114 |         """Load prefs from SQLite JSON and merge into self.prefs (only known keys)."""
  115 |         if not self._sqlite_handler or not self._companion_hash:
  116 |             return
  117 |         try:
  118 |             stored = self._sqlite_handler.companion_load_prefs(self._companion_hash)
  119 |             if not stored or not isinstance(stored, dict):
  120 |                 return
  121 |             for key, value in stored.items():
```
### Evidence 2: `src/openhop_core/companion/base_config.py` lines 35–47

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/companion/base_config.py#L35-L47)

```text
   35 |     def set_advert_name(self, name: str) -> None:
   36 |         """Set the node's advertised name.
   37 | 
   38 |         Firmware stores this in a fixed ``char node_name[32]`` (NodePrefs.h),
   39 |         so the limit is 31 *bytes* of UTF-8, not 31 characters. Truncate on
   40 |         the encoded bytes and decode leniently so a multi-byte codepoint
   41 |         straddling the cut is dropped whole rather than split.
   42 |         """
   43 |         self.prefs.node_name = name.encode("utf-8")[:NODE_NAME_MAX_BYTES].decode(
   44 |             "utf-8", errors="ignore"
   45 |         )
   46 |         self._save_prefs()
   47 | 
```

