# BUG-020 — An update install can overlap a version check and be reported idle while still running

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Self-update state machine |
| Components | OpenHop Repeater Web API |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Install rejects only an existing `installing` state. It can replace `checking`, and the older check thread later resets the shared state to `idle` while installation continues.

## What happens now

`start_install()` accepts every state except `installing`. `_finish_check()` unconditionally writes `state="idle"`. The API therefore permits check→install overlap; completion order determines the visible state and can enable a second install while the first one is active.

## Expected behaviour / proposed direction

Only one updater operation may own the state. Completion from an obsolete worker must not mutate the current job.

## What needs to change

Use an explicit transition table plus monotonically increasing operation IDs. `finish_check(id, ...)` and `finish_install(id, ...)` should no-op unless the ID and operation type still match.

## Reproduction / verification

The deeper focused check set state to `checking`, successfully started an install, then completed the old check. State became `idle` instead of remaining `installing`.

## Suggested code change

> **Review warning:** the linked patch is an LLM-generated implementation sketch. It is intended to show the approximate change surface, not to be applied blindly. Rebase it onto the current source, add regression tests, and review concurrency, persistence and protocol implications.

[Open the suggested patch](../patches/BUG-020.patch)

## Source references and excerpts

### Evidence 1: `repeater/web/update_endpoints.py` lines 393–447

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

### Evidence 2: `repeater/web/update_endpoints.py` lines 769–788

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

### Evidence 3: `repeater/web/update_endpoints.py` lines 1143–1192

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/update_endpoints.py#L1143-L1192)

```text
 1143 |     # POST /api/update/install                                             #
 1144 |     # ------------------------------------------------------------------ #
 1145 |     @cherrypy.expose
 1146 |     @cherrypy.tools.json_out()
 1147 |     @cherrypy.tools.json_in()
 1148 |     def install(self, **kwargs):
 1149 | 
 1150 |         if cherrypy.request.method == "OPTIONS":
 1151 |             return ""
 1152 | 
 1153 |         try:
 1154 |             self._require_post()
 1155 |         except cherrypy.HTTPError:
 1156 |             raise
 1157 | 
 1158 |         body = {}
 1159 |         try:
 1160 |             body = cherrypy.request.json or {}
 1161 |         except Exception as exc:
 1162 |             logger.debug(f"[Update] Ignoring non-JSON update install payload: {exc}")
 1163 | 
 1164 |         snap = _state.snapshot()
 1165 | 
 1166 |         if snap["state"] == "installing":
 1167 |             return self._err("An update is already in progress", 409)
 1168 | 
 1169 |         force = bool(body.get("force", False))
 1170 |         if not force and not snap["has_update"]:
 1171 |             # Still allow install if no check has been done yet
 1172 |             if snap["latest_version"] is not None:
 1173 |                 return self._err(
 1174 |                     f"Already up to date ({snap['current_version']}). "
 1175 |                     'Pass {"force": true} to reinstall anyway.',
 1176 |                     409,
 1177 |                 )
 1178 | 
 1179 |         t = threading.Thread(target=_do_install, daemon=True, name="update-install")
 1180 |         started = _state.start_install(t)
 1181 |         if not started:
 1182 |             return self._err("Could not start install thread – check state", 409)
 1183 | 
 1184 |         t.start()
 1185 |         logger.warning(f"[Update] Install triggered via API – channel={_state.channel}")
 1186 |         return self._ok(
 1187 |             {
 1188 |                 "message": f"Update started on channel '{_state.channel}'. "
 1189 |                 "Watch /api/update/progress for live output.",
 1190 |                 "state": "installing",
 1191 |             }
 1192 |         )
```
