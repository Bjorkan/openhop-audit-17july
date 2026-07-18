# BUG-011 — GPS wall-clock corrections can invalidate rolling airtime and rate-limit windows

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. The finding survived an independent static runtime trace, executable reproduction and active falsification pass on 18 July 2026.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | Timekeeping / safety limits |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Independent recheck | 2026-07-18 |
| Status | Open in supplied snapshot |

## TL;DR

Relative safety windows use mutable wall-clock time even though the service can change `CLOCK_REALTIME` from GPS by default.

## What happens now

A forward clock correction makes old TX records, advert dedupe entries, token-bucket timestamps and penalties appear expired immediately. A backward correction can hold them active much longer than intended. The airtime limiter can consequently allow a second full budget without 60 seconds of real elapsed time.

## Expected behaviour / proposed direction

Elapsed-time logic must use a monotonic clock. Wall clock should be reserved for persisted/event timestamps displayed to users.

## What needs to change

Convert AirtimeManager, advert limiter and other in-process cooldowns to `time.monotonic()`; inject the clock for deterministic tests. Keep UTC timestamps separately where needed.

## Reproduction / verification

Focused check placed a full airtime budget at wall time 100 and simulated a forward correction to 1000; the history was discarded and another full budget was allowed immediately.

See [`docs/REVERIFICATION-CHECKS.md`](../docs/REVERIFICATION-CHECKS.md) and the executable check script.

## Triple verification

| Method | Result | Record |
|---|---|---|
| Static runtime trace | **Passed** | The complete reachable path and exact quoted source excerpts in this report were revalidated byte-for-byte against the supplied source trees. |
| Executable reproduction | **Passed** | `test_bug_011_confirmed_realtime_jump_invalidates_relative_airtime_window` in [`REVERIFICATION-CHECKS.py`](../docs/REVERIFICATION-CHECKS.py). |
| Active falsification | **Passed** | The limiter uses mutable realtime while the supplied GPS service can change that same clock. See [`BASELINE-FALSIFICATION-CHECKS.py`](../docs/BASELINE-FALSIFICATION-CHECKS.py). |

The consolidated baseline matrix and captured results are in [`BASELINE-TRIPLE-VERIFICATION.md`](../docs/BASELINE-TRIPLE-VERIFICATION.md).

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-011/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/airtime.py` lines 70–97

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/airtime.py#L70-L97)

```text
   70 |     def can_transmit(self, airtime_ms: float) -> Tuple[bool, float]:
   71 |         enforcement_enabled = self.config.get("duty_cycle", {}).get("enforcement_enabled", True)
   72 |         if not enforcement_enabled:
   73 |             # Duty cycle enforcement disabled - always allow
   74 |             return True, 0.0
   75 | 
   76 |         now = time.time()
   77 | 
   78 |         # Remove old entries outside window
   79 |         self.tx_history = [(ts, at) for ts, at in self.tx_history if now - ts < self.window_size]
   80 | 
   81 |         # Calculate current airtime in window
   82 |         current_airtime = sum(at for _, at in self.tx_history)
   83 | 
   84 |         if current_airtime + airtime_ms <= self.max_airtime_per_minute:
   85 |             return True, 0.0
   86 | 
   87 |         # Calculate wait time until oldest entry expires
   88 |         if self.tx_history:
   89 |             oldest_ts, oldest_at = self.tx_history[0]
   90 |             wait_time = (oldest_ts + self.window_size) - now
   91 |             return False, max(0, wait_time)
   92 | 
   93 |         return False, 1.0
   94 | 
   95 |     def record_tx(self, airtime_ms: float):
   96 |         self.tx_history.append((time.time(), airtime_ms))
   97 |         self.total_airtime_ms += airtime_ms
```

### Evidence 2: `repeater/data_acquisition/gps_service.py` lines 193–197

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/data_acquisition/gps_service.py#L193-L197)

```text
  193 | def _set_system_clock_from_datetime(value: datetime):
  194 |     if not hasattr(time, "clock_settime") or not hasattr(time, "CLOCK_REALTIME"):
  195 |         raise RuntimeError("time.clock_settime(CLOCK_REALTIME) is not available")
  196 |     time.clock_settime(time.CLOCK_REALTIME, value.timestamp())
  197 | 
```

### Evidence 3: `repeater/data_acquisition/gps_service.py` lines 1204–1265

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/data_acquisition/gps_service.py#L1204-L1265)

```text
 1204 |     def _maybe_sync_system_time(self):
 1205 |         if not self.enabled or not self.time_sync_enabled:
 1206 |             return
 1207 | 
 1208 |         now_monotonic = time.monotonic()
 1209 |         with self._time_sync_lock:
 1210 |             if (
 1211 |                 self._last_time_sync_monotonic is not None
 1212 |                 and now_monotonic - self._last_time_sync_monotonic < self.time_sync_interval_seconds
 1213 |             ):
 1214 |                 return
 1215 | 
 1216 |         snapshot = self.parser.snapshot()
 1217 |         if not snapshot.get("status", {}).get("fix_valid"):
 1218 |             return
 1219 | 
 1220 |         gps_time = _parse_datetime_utc(snapshot.get("time", {}).get("datetime_utc"))
 1221 |         if gps_time is None:
 1222 |             return
 1223 | 
 1224 |         if gps_time.year < self.time_sync_min_valid_year:
 1225 |             self._record_time_sync_status(
 1226 |                 state="ignored",
 1227 |                 gps_time=gps_time,
 1228 |                 error=(
 1229 |                     f"GPS time year {gps_time.year} is older than "
 1230 |                     f"minimum {self.time_sync_min_valid_year}"
 1231 |                 ),
 1232 |             )
 1233 |             return
 1234 | 
 1235 |         system_now = self._time_provider()
 1236 |         offset_seconds = gps_time.timestamp() - system_now
 1237 |         self._last_time_sync_monotonic = now_monotonic
 1238 |         if abs(offset_seconds) < self.time_sync_min_offset_seconds:
 1239 |             self._record_time_sync_status(
 1240 |                 state="in_sync",
 1241 |                 gps_time=gps_time,
 1242 |                 offset_seconds=offset_seconds,
 1243 |                 success=True,
 1244 |             )
 1245 |             return
 1246 | 
 1247 |         try:
 1248 |             self._clock_setter(gps_time)
 1249 |         except Exception as exc:
 1250 |             self._record_time_sync_status(
 1251 |                 state="error",
 1252 |                 gps_time=gps_time,
 1253 |                 offset_seconds=offset_seconds,
 1254 |                 error=f"{type(exc).__name__}: {exc}",
 1255 |             )
 1256 |             logger.warning("GPS system time sync failed: %s", exc)
 1257 |             return
 1258 | 
 1259 |         self._record_time_sync_status(
 1260 |             state="synced",
 1261 |             gps_time=gps_time,
 1262 |             offset_seconds=offset_seconds,
 1263 |             success=True,
 1264 |         )
 1265 |         self.parser.last_update = self._time_provider()
```

### Evidence 4: `repeater/config.py` lines 262–277

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config.py#L262-L277)

```text
  262 |             "host": "",
  263 |             "port": 80,
  264 |             "endpoint": "/api/stats",
  265 |             "scheme": "http",
  266 |             "username": "admin",
  267 |             "password": None,
  268 |             "stale_after_seconds": 10.0,
  269 |             "retain_sentences": 25,
  270 |             "validate_checksum": True,
  271 |             "require_checksum": False,
  272 |             "time_sync_enabled": True,
  273 |             "time_sync_interval_seconds": 3600.0,
  274 |             "time_sync_min_offset_seconds": 1.0,
  275 |             "time_sync_min_valid_year": 2020,
  276 |             "persist_gps_fix_to_config": False,
  277 |             "persist_gps_fix_interval_seconds": 600.0,
```

### Evidence 5: `repeater/handler_helpers/advert.py` lines 430–480

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/advert.py#L430-L480)

```text
  430 |             self._stats_adverts_dropped += 1
  431 |             return False, f"advert penalty box active ({remaining:.1f}s remaining)"
  432 | 
  433 |         state = self._refill_tokens_if_needed(pubkey, now)
  434 |         _, _, _, min_interval = self._get_effective_limits()
  435 | 
  436 |         last_seen = float(state.get("last_seen", 0.0))
  437 |         if min_interval > 0 and last_seen > 0:
  438 |             since_last = now - last_seen
  439 |             if since_last < min_interval:
  440 |                 self._record_violation_and_maybe_penalize(pubkey, now)
  441 |                 self._stats_adverts_dropped += 1
  442 |                 return (
  443 |                     False,
  444 |                     f"advert min-interval hit ({since_last:.2f}s < {min_interval:.2f}s)",
  445 |                 )
  446 | 
  447 |         if state["tokens"] < 1.0:
  448 |             self._record_violation_and_maybe_penalize(pubkey, now)
  449 |             self._stats_adverts_dropped += 1
  450 |             return False, "advert rate limit exceeded"
  451 | 
  452 |         state["tokens"] -= 1.0
  453 |         state["last_seen"] = now
  454 |         self._stats_adverts_allowed += 1
  455 |         return True, ""
  456 | 
  457 |     def record_packet_seen(self, is_duplicate: bool = False) -> None:
  458 |         """Record a packet seen for metrics (called by router for non-advert packets)."""
  459 |         now = time.time()
  460 |         self._update_metrics_window(now, is_advert=False, is_duplicate=is_duplicate)
  461 | 
  462 |     def get_rate_limit_stats(self) -> dict:
  463 |         """Get comprehensive rate limiting and adaptive tier statistics."""
  464 |         now = time.time()
  465 |         bucket_cap, refill_tokens, refill_interval, min_interval = self._get_effective_limits()
  466 | 
  467 |         # Active penalties
  468 |         active_penalties = {
  469 |             pk[:16]: round(until - now, 1)
  470 |             for pk, until in self._penalty_until.items()
  471 |             if until > now
  472 |         }
  473 | 
  474 |         # Per-pubkey bucket states
  475 |         bucket_summary = {}
  476 |         for pk, state in self._bucket_state.items():
  477 |             bucket_summary[pk[:16]] = {
  478 |                 "tokens": round(state["tokens"], 2),
  479 |                 "last_seen_ago": round(now - state["last_seen"], 1)
  480 |                 if state["last_seen"] > 0
```
