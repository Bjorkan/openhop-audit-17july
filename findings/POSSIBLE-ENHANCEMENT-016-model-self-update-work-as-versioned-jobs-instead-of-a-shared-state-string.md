# POSSIBLE-ENHANCEMENT-016 — Possible enhancement — model self-update work as versioned jobs instead of a shared state string

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Self-update architecture |
| Components | OpenHop Repeater Web API |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Checks and installs mutate one singleton through loosely constrained methods, with no ownership token tying completion to the operation that started it.

## What happens now

Threads can finish out of order; channel changes and persistence are independent of worker generation. A single string cannot distinguish current from stale work.

## Expected behaviour / proposed direction

Represent each check/install as a job containing ID, type, channel, start time and terminal result. Only the current job may update public state.

## What needs to change

Prevents stale completions, supports cancellation/history and simplifies progress/API responses.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-016/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/web/update_endpoints.py` lines 351–410

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/update_endpoints.py#L351-L410)

```text
  351 |     def _save_channel(self, channel: str) -> None:
  352 |         try:
  353 |             os.makedirs(os.path.dirname(_CHANNELS_FILE), exist_ok=True)
  354 |             with open(_CHANNELS_FILE, "w") as fh:
  355 |                 fh.write(channel)
  356 |         except OSError as exc:
  357 |             logger.warning(f"Could not persist channel choice: {exc}")
  358 | 
  359 |     # ------------------------------------------------------------------ #
  360 |     # Thread-safe accessors                                                #
  361 |     # ------------------------------------------------------------------ #
  362 |     def snapshot(self) -> dict:
  363 |         with self._lock:
  364 |             # Always read installed version fresh so it reflects post-restart state
  365 |             fresh_current = _get_installed_version()
  366 |             if fresh_current != "unknown":
  367 |                 self.current_version = fresh_current
  368 |                 # Recompute has_update with fresh installed version
  369 |                 if self.latest_version is not None:
  370 |                     self.has_update = _has_update(self.current_version, self.latest_version)
  371 |             return {
  372 |                 "current_version": self.current_version,
  373 |                 "latest_version": self.latest_version,
  374 |                 "has_update": self.has_update,
  375 |                 "channel": self.channel,
  376 |                 "last_checked": self.last_checked.isoformat() if self.last_checked else None,
  377 |                 "state": self.state,
  378 |                 "error": self.error_message,
  379 |                 "rate_limit_until": self.rate_limit_until.isoformat()
  380 |                 if self.rate_limit_until
  381 |                 else None,
  382 |             }
  383 | 
  384 |     def set_channel(self, channel: str) -> None:
  385 |         with self._lock:
  386 |             self.channel = channel
  387 |             self._save_channel(channel)
  388 |             # Invalidate cached check so next call re-checks against new channel
  389 |             self.last_checked = None
  390 |             self.latest_version = None
  391 |             self.has_update = False
  392 | 
  393 |     def _set_checking(self) -> bool:
  394 |         """Return True and move to 'checking' if currently idle."""
  395 |         with self._lock:
  396 |             if self.state not in ("idle", "complete", "error"):
  397 |                 return False
  398 |             self.state = "checking"
  399 |             return True
  400 | 
  401 |     def _finish_check(self, latest: str) -> None:
  402 |         with self._lock:
  403 |             self.latest_version = latest
  404 |             fresh = _get_installed_version()
  405 |             if fresh != "unknown":
  406 |                 self.current_version = fresh
  407 |             self.has_update = _has_update(self.current_version, latest)
  408 |             self.last_checked = datetime.now(timezone.utc)
  409 |             self.state = "idle"
  410 |             self.error_message = None
```

### Evidence 2: `repeater/web/update_endpoints.py` lines 393–447

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/update_endpoints.py#L393-L447)

```text
  393 |     def _set_checking(self) -> bool:
  394 |         """Return True and move to 'checking' if currently idle."""
  395 |         with self._lock:
  396 |             if self.state not in ("idle", "complete", "error"):
  397 |                 return False
  398 |             self.state = "checking"
  399 |             return True
  400 | 
  401 |     def _finish_check(self, latest: str) -> None:
  402 |         with self._lock:
  403 |             self.latest_version = latest
  404 |             fresh = _get_installed_version()
  405 |             if fresh != "unknown":
  406 |                 self.current_version = fresh
  407 |             self.has_update = _has_update(self.current_version, latest)
  408 |             self.last_checked = datetime.now(timezone.utc)
  409 |             self.state = "idle"
  410 |             self.error_message = None
  411 | 
  412 |     def _fail_check(self, msg: str) -> None:
  413 |         with self._lock:
  414 |             self.state = "error"
  415 |             self.error_message = msg
  416 |             self.last_checked = datetime.now(timezone.utc)
  417 | 
  418 |     def _fail_check_ratelimit(self, msg: str, reset_at: Optional[datetime]) -> None:
  419 |         """Like _fail_check but keeps existing version data intact and records
  420 |         the reset time so we don't hammer GitHub until the window expires."""
  421 |         with self._lock:
  422 |             # Keep state as idle so the UI still shows version info
  423 |             self.state = "idle"
  424 |             self.error_message = msg
  425 |             self.last_checked = datetime.now(timezone.utc)
  426 |             self.rate_limit_until = reset_at
  427 | 
  428 |     def start_install(self, thread: threading.Thread) -> bool:
  429 |         with self._lock:
  430 |             if self.state == "installing":
  431 |                 return False
  432 |             self.state = "installing"
  433 |             self.error_message = None
  434 |             self.progress_lines = ["[pyMC updater] Starting update…"]
  435 |             self._install_thread = thread
  436 |             return True
  437 | 
  438 |     def finish_install(self, success: bool, msg: str) -> None:
  439 |         with self._lock:
  440 |             self.state = "complete" if success else "error"
  441 |             self.error_message = None if success else msg
  442 |             if success:
  443 |                 self.progress_lines.append(f"[pyMC updater] ✓ {msg}")
  444 |                 self.has_update = False
  445 |                 # current_version will be refreshed on next snapshot() call
  446 |             else:
  447 |                 self.progress_lines.append(f"[pyMC updater] ✗ {msg}")
```

### Evidence 3: `repeater/web/update_endpoints.py` lines 769–788

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/update_endpoints.py#L769-L788)

```text
  769 | def _do_check() -> None:
  770 |     """Background thread: fetch latest version and update state."""
  771 |     channel = _state.channel
  772 |     try:
  773 |         latest = _fetch_latest_version(channel)
  774 |         # Successful fetch — clear any previous rate-limit hold
  775 |         with _state._lock:
  776 |             _state.rate_limit_until = None
  777 |         _state._finish_check(latest)
  778 |         logger.info(
  779 |             f"[Update] Check complete – installed={_state.current_version} "
  780 |             f"latest={latest} channel={channel} has_update={_state.has_update}"
  781 |         )
  782 |     except _RateLimitError as exc:
  783 |         logger.warning(f"[Update] {exc}")
  784 |         _state._fail_check_ratelimit(str(exc), exc.reset_at)
  785 |     except Exception as exc:
  786 |         msg = str(exc)
  787 |         _state._fail_check(msg)
  788 |         logger.warning(f"[Update] Version check failed: {msg}")
```
