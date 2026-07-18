# BUG-042 — RRD `COUNTER` rates are treated as cumulative counter values

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | Historical metrics / RRD |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |

## TL;DR

RRD data sources are declared `COUNTER`, so fetched values are rates after RRD normalization. Readers subtract fetched samples as if they were monotonically increasing raw counters. Constant non-zero traffic consequently produces zero packet totals and empty dashboard buckets.

## Expected behavior

Historical totals must integrate rates over step duration, or the RRD schema must store a data-source type whose fetched values match reader assumptions.

## Required direction

1. Choose one consistent model: integrate `COUNTER` rates by step, or migrate to appropriate `GAUGE`/`DERIVE` semantics and update writers.
2. Centralize conversion of RRD rows into counts so API readers cannot drift.
3. Plan migration/version handling for existing RRD files.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | RRD datasource to readers | **Passed** | RRD declares `COUNTER`, which returns rates, but both readers subtract successive fetched values as though they were cumulative counters. |
| Executable reproduction | Packet-type reader | **Passed** | Ten constant non-zero rate samples produce a total of zero. |
| Active falsification | Independent dashboard aggregation | **Passed** | Constant RX/TX rates produce zero in every dashboard bucket, confirming the contradiction in a separate consumer. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-042/implementation_plan.md`](../implementation-plans/BUG-042/implementation_plan.md).

## Source evidence

### Evidence 1: `repeater/data_acquisition/rrdtool_handler.py` lines 39–71

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/data_acquisition/rrdtool_handler.py#L39-L71)

```text
   39 | 
   40 |         try:
   41 |             rrdtool.create(
   42 |                 str(self.rrd_path),
   43 |                 "--step",
   44 |                 "60",
   45 |                 "--start",
   46 |                 str(int(time.time() - 60)),
   47 |                 "DS:rx_count:COUNTER:120:0:U",
   48 |                 "DS:tx_count:COUNTER:120:0:U",
   49 |                 "DS:drop_count:COUNTER:120:0:U",
   50 |                 "DS:avg_rssi:GAUGE:120:-200:0",
   51 |                 "DS:avg_snr:GAUGE:120:-30:30",
   52 |                 "DS:avg_length:GAUGE:120:0:256",
   53 |                 "DS:avg_score:GAUGE:120:0:1",
   54 |                 "DS:neighbor_count:GAUGE:120:0:U",
   55 |                 "DS:type_0:COUNTER:120:0:U",
   56 |                 "DS:type_1:COUNTER:120:0:U",
   57 |                 "DS:type_2:COUNTER:120:0:U",
   58 |                 "DS:type_3:COUNTER:120:0:U",
   59 |                 "DS:type_4:COUNTER:120:0:U",
   60 |                 "DS:type_5:COUNTER:120:0:U",
   61 |                 "DS:type_6:COUNTER:120:0:U",
   62 |                 "DS:type_7:COUNTER:120:0:U",
   63 |                 "DS:type_8:COUNTER:120:0:U",
   64 |                 "DS:type_9:COUNTER:120:0:U",
   65 |                 "DS:type_10:COUNTER:120:0:U",
   66 |                 "DS:type_11:COUNTER:120:0:U",
   67 |                 "DS:type_12:COUNTER:120:0:U",
   68 |                 "DS:type_13:COUNTER:120:0:U",
   69 |                 "DS:type_14:COUNTER:120:0:U",
   70 |                 "DS:type_15:COUNTER:120:0:U",
   71 |                 "DS:type_other:COUNTER:120:0:U",
```
### Evidence 2: `repeater/data_acquisition/rrdtool_handler.py` lines 259–281

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/data_acquisition/rrdtool_handler.py#L259-L281)

```text
  259 |             for type_key, data_points in rrd_data["packet_types"].items():
  260 |                 valid_points = [p for p in data_points if p is not None]
  261 |                 total_valid_points += len(valid_points)
  262 | 
  263 |             if total_valid_points < 10:
  264 |                 logger.warning(f"RRD data too sparse ({total_valid_points} valid points)")
  265 |                 return None
  266 | 
  267 |             for type_key, data_points in rrd_data["packet_types"].items():
  268 |                 valid_points = [p for p in data_points if p is not None]
  269 | 
  270 |                 if len(valid_points) >= 2:
  271 |                     total = max(valid_points) - min(valid_points)
  272 |                 elif len(valid_points) == 1:
  273 |                     total = valid_points[0]
  274 |                 else:
  275 |                     total = 0
  276 | 
  277 |                 type_name = packet_type_names.get(type_key, type_key)
  278 |                 type_totals[type_name] = max(0, total or 0)
  279 | 
  280 |             result = {
  281 |                 "hours": hours,
```
### Evidence 3: `repeater/web/api_endpoints.py` lines 490–516

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L490-L516)

```text
  490 |             return {}
  491 | 
  492 |         def _counter_delta(values: list) -> list[float]:
  493 |             output = []
  494 |             previous = None
  495 |             for item in values:
  496 |                 if item is None:
  497 |                     output.append(0.0)
  498 |                 elif previous is None:
  499 |                     output.append(0.0)
  500 |                     previous = item
  501 |                 else:
  502 |                     output.append(float(max(0, item - previous)))
  503 |                     previous = item
  504 |             return output
  505 | 
  506 |         rx_values = _counter_delta(metrics.get("rx_count", []))
  507 |         tx_values = _counter_delta(metrics.get("tx_count", []))
  508 |         drop_values = _counter_delta(metrics.get("drop_count", []))
  509 |         rssi_values = metrics.get("avg_rssi", []) or []
  510 |         snr_values = metrics.get("avg_snr", []) or []
  511 | 
  512 |         bucket_map: dict = {}
  513 | 
  514 |         max_len = len(timestamps)
  515 |         for i in range(max_len):
  516 |             ts = int(timestamps[i])
```

