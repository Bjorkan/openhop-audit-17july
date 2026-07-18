from __future__ import annotations
import os

import inspect
import json
import sys
import threading
import time
from pathlib import Path

CORE = Path(os.environ["OPENHOP_CORE_ROOT"]).resolve()
REP = Path(os.environ["OPENHOP_REPEATER_ROOT"]).resolve()
sys.path.insert(0, str(CORE / 'src'))
sys.path.insert(0, str(REP))

from repeater.data_acquisition.rrdtool_handler import RRDToolHandler
from repeater.web.api_endpoints import APIEndpoints
import repeater.data_acquisition.websocket_handler as ws

checks: list[tuple[str, str, bool, str]] = []

def check(fid: str, method: str, ok: bool, detail: str) -> None:
    checks.append((fid, method, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'} [{fid}] {method}: {detail}")


def validate_websocket_heartbeat_restart() -> None:
    fid = 'WEBSOCKET-HEARTBEAT-THREAD-DUPLICATION'
    shutdown_src = inspect.getsource(ws.shutdown_websocket)
    loop_src = inspect.getsource(ws._heartbeat_loop)
    ok = (
        '_heartbeat_running = False' in shutdown_src
        and '_heartbeat_thread = None' in shutdown_src
        and '.join(' not in shutdown_src
        and 'while _heartbeat_running' in loop_src
        and 'time.sleep(PING_INTERVAL)' in loop_src
    )
    check(fid, 'static-shared-flag-without-join', ok,
          'Shutdown drops the thread reference without joining; old and new loops share the same restartable boolean.')

    class Client:
        def __init__(self):
            self.calls = 0
            self.lock = threading.Lock()
        def send(self, message):
            with self.lock:
                self.calls += 1

    old_interval = ws.PING_INTERVAL
    old_clients = ws._connected_clients
    try:
        ws.PING_INTERVAL = 0.03
        client = Client()
        ws._connected_clients = {client}
        ws._heartbeat_running = True
        t1 = threading.Thread(target=ws._heartbeat_loop, daemon=True, name='audit-heartbeat-1')
        t1.start()
        # Reproduce shutdown->immediate-start before t1's sleep returns.
        time.sleep(0.005)
        ws._heartbeat_running = False
        dropped_while_alive = t1.is_alive()
        ws._heartbeat_running = True
        t2 = threading.Thread(target=ws._heartbeat_loop, daemon=True, name='audit-heartbeat-2')
        t2.start()
        time.sleep(0.08)
        both_alive = t1.is_alive() and t2.is_alive()
        check(fid, 'dynamic-immediate-restart-keeps-old-thread', dropped_while_alive and both_alive,
              f'old_alive_when_reference_would_be_dropped={dropped_while_alive}, both_alive_after_restart={both_alive}')

        # A single thread can send at most roughly ceil(0.08/0.03)=3 pings; two produce >=4 reliably.
        calls = client.calls
        check(fid, 'observable-duplicate-heartbeats', calls >= 4,
              f'ping_sends_in_80ms={calls}; both surviving loops send to the same client set')
    finally:
        ws._heartbeat_running = False
        for t in [locals().get('t1'), locals().get('t2')]:
            if t is not None:
                t.join(timeout=0.2)
        ws.PING_INTERVAL = old_interval
        ws._connected_clients = old_clients


def validate_rrd_counter_interpretation() -> None:
    fid = 'RRD-COUNTERS-INTERPRETED-AS-CUMULATIVE-VALUES'
    init_src = inspect.getsource(RRDToolHandler._init_rrd)
    stats_src = inspect.getsource(RRDToolHandler.get_packet_type_stats)
    bucket_src = inspect.getsource(APIEndpoints._build_rrd_bucket_metrics)
    ok = (
        'DS:type_0:COUNTER' in init_src
        and 'max(valid_points) - min(valid_points)' in stats_src
        and 'item - previous' in bucket_src
    )
    check(fid, 'static-datasource-vs-reader-semantics', ok,
          'RRD data sources are COUNTER, whose fetched values are rates, but both readers subtract fetched samples as if cumulative totals.')

    # Isolate the stats reader. A constant non-zero packet rate over 10 samples must not total zero.
    h = RRDToolHandler.__new__(RRDToolHandler)
    h.get_data = lambda *_a, **_k: {
        'packet_types': {'type_2': [2.0] * 10},
        'step': 60,
        'timestamps': list(range(10)),
    }
    stats = h.get_packet_type_stats(hours=1)
    ok = stats is not None and stats['packet_type_totals']['Plain Text Message (TXT_MSG)'] == 0
    check(fid, 'dynamic-packet-type-total-collapses-constant-rate', ok,
          f"constant fetched rate=2.0 for 10 samples produced total={stats['total_packets'] if stats else None}, although traffic is non-zero")

    # Exercise the dashboard bucket conversion independently.
    api = APIEndpoints.__new__(APIEndpoints)
    rrd = {
        'timestamps': [0, 60, 120, 180],
        'metrics': {
            'rx_count': [1.5, 1.5, 1.5, 1.5],
            'tx_count': [0.5, 0.5, 0.5, 0.5],
            'drop_count': [0.0, 0.0, 0.0, 0.0],
            'avg_rssi': [-90.0] * 4,
            'avg_snr': [5.0] * 4,
        },
    }
    buckets = api._build_rrd_bucket_metrics(rrd, 60)
    rx_total = sum(v['rx_count'] for v in buckets.values())
    tx_total = sum(v['tx_count'] for v in buckets.values())
    ok = rx_total == 0.0 and tx_total == 0.0
    check(fid, 'dashboard-buckets-drop-steady-traffic', ok,
          f'constant non-zero fetched rates produced rx_total={rx_total}, tx_total={tx_total}')


def main() -> None:
    validate_websocket_heartbeat_restart()
    validate_rrd_counter_interpretation()
    print('\nSUMMARY')
    fids = sorted({c[0] for c in checks})
    for fid in fids:
        own = [c for c in checks if c[0] == fid]
        print(f'{fid}: {sum(c[2] for c in own)}/{len(own)}')
    if not all(c[2] for c in checks):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
