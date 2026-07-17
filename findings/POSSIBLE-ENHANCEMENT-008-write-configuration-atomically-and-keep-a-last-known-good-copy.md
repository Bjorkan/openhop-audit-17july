# POSSIBLE-ENHANCEMENT-008 — Possible enhancement — write configuration atomically and keep a last-known-good copy

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Persistence robustness |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Configuration is written directly to the target YAML file.

## What happens now

A process crash, full filesystem or interrupted write can leave the only configuration file truncated or partially written.

## Expected behaviour / proposed direction

Serialize and fsync a temporary file in the same directory, validate it, then `os.replace()` it; retain a bounded `.bak` copy.

## What needs to change

Provides atomic replacement and recovery without changing the public configuration format.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-008/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/config_manager.py` lines 227–252

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config_manager.py#L227-L252)

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
```
