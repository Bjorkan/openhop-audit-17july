# BUG-022 — Update-channel persistence failure is hidden behind a success response

[← Audit index](../README.md)

> Reverification verdict: **Confirmed against the supplied snapshot.**

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Self-update persistence / UI contract |
| Components | OpenHop Repeater Web API |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Saving the selected update channel catches filesystem errors and returns no result. Runtime state changes anyway and the endpoint always reports that the channel switched.

## What happens now

On read-only storage, permission failure or disk error, the running process uses the new channel until restart, while the persisted file remains unchanged. The UI receives success and has no way to know the selection will revert.

## Expected behaviour / proposed direction

The endpoint should report success only after durable persistence, or explicitly return a volatile runtime-only result.

## What needs to change

Make `_save_channel()` return a boolean or raise; persist atomically before changing shared runtime state; return an HTTP error on failure.

## Reproduction / verification

The deeper focused check forced `_save_channel()` to fail. The endpoint still returned `success=true` and changed the runtime channel.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-022/implementation_plan.md)


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

### Evidence 2: `repeater/web/update_endpoints.py` lines 1279–1315

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/update_endpoints.py#L1279-L1315)

```text
 1279 |     # ------------------------------------------------------------------ #
 1280 |     # POST /api/update/set_channel                                         #
 1281 |     # ------------------------------------------------------------------ #
 1282 |     @cherrypy.expose
 1283 |     @cherrypy.tools.json_out()
 1284 |     @cherrypy.tools.json_in()
 1285 |     def set_channel(self, **kwargs):
 1286 | 
 1287 |         if cherrypy.request.method == "OPTIONS":
 1288 |             return ""
 1289 | 
 1290 |         try:
 1291 |             self._require_post()
 1292 |         except cherrypy.HTTPError:
 1293 |             raise
 1294 | 
 1295 |         body = {}
 1296 |         try:
 1297 |             body = cherrypy.request.json or {}
 1298 |         except Exception as exc:
 1299 |             logger.debug(f"[Update] Ignoring non-JSON update channel payload: {exc}")
 1300 | 
 1301 |         channel = str(body.get("channel", "")).strip()
 1302 |         if not channel:
 1303 |             return self._err("'channel' field is required")
 1304 | 
 1305 |         if _state.state == "installing":
 1306 |             return self._err("Cannot change channel while an install is in progress", 409)
 1307 | 
 1308 |         _state.set_channel(channel)
 1309 |         logger.info(f"[Update] Channel changed to '{channel}' via API")
 1310 |         return self._ok(
 1311 |             {
 1312 |                 "channel": channel,
 1313 |                 "message": f"Channel switched to '{channel}'. Run /api/update/check to verify.",
 1314 |             }
 1315 |         )
```
