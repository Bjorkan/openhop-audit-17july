# POSSIBLE-ENHANCEMENT-006 — Possible enhancement — inject a clock for relative timers

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Timekeeping and testing |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Many subsystems call `time.time()` directly for both event timestamps and elapsed-time decisions.

## What happens now

This couples tests and control flow to the mutable system clock and makes GPS/NTP corrections hard to reason about.

## Expected behaviour / proposed direction

Inject a small clock object exposing `wall_time()` and `monotonic()`; use the latter for deadlines, TTLs and rate limits.

## What needs to change

Improves determinism, makes time-jump tests trivial, and documents whether each timestamp is persistent or relative.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-006/implementation_plan.md)


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

### Evidence 2: `repeater/handler_helpers/advert.py` lines 430–480

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
