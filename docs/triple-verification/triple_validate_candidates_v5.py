import os
import asyncio
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

CORE = Path(os.environ["OPENHOP_CORE_ROOT"]).resolve()
REP = Path(os.environ["OPENHOP_REPEATER_ROOT"]).resolve()
sys.path.insert(0,str(CORE/'src'))
sys.path.insert(0,str(REP))

results=[]
def check(cond,key,method,detail):
    passed=bool(cond)
    results.append((key,method,passed,detail))
    print(f"{'PASS' if passed else 'FAIL'} [{key}] {method}: {detail}")

# ---------------------------------------------------------------------------
# Mesh CLI documents frequency as MHz, but persists the raw value as Hz.
# ---------------------------------------------------------------------------
key='MESHCLI-FREQUENCY-UNIT-MISMATCH'
mesh_path=REP/'repeater/handler_helpers/mesh_cli.py'
mesh=mesh_path.read_text()
check(
    'set freq <mhz>' in mesh
    and 'freq_hz / 1_000_000.0' in mesh
    and 'self.config["radio"]["frequency"] = float(value)' in mesh,
    key,'static-help-getter-setter-contract',
    'Help declares MHz and get converts stored Hz to MHz, but set stores the raw MHz token without multiplying by 1,000,000.'
)

from repeater.config_manager import ConfigManager
from repeater.handler_helpers.mesh_cli import MeshCLI
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'config.yaml'
    cfg={
        'repeater': {'node_name':'n','name':'n','mode':'forward'},
        'mesh':{},
        'radio': {'frequency':869_618_000,'bandwidth':62_500,'spreading_factor':8,'coding_rate':8,'tx_power':14},
        'security':{},
    }
    mgr=ConfigManager(str(p),cfg)
    cli=MeshCLI(str(p),cfg,mgr)
    reply=cli.handle_command(b'X','set freq 869.618',True)
    persisted=p.read_text() if p.exists() else ''
    check(
        cfg['radio']['frequency']==869.618 and 'frequency: 869.618' in persisted,
        key,'real-public-command-persistence',
        f'reply={reply!r}; runtime_value={cfg["radio"]["frequency"]!r}; persisted frequency is 869.618 rather than 869618000.'
    )

# Countercheck the actual runtime ConfigManager conversion/application path.
class FakeRadio:
    def __init__(self):
        self.frequency=869_618_000
        self.bandwidth=62_500
        self.spreading_factor=8
        self.coding_rate=8
        self.tx_power=14
        self.calls=[]
    def set_frequency(self,v): self.calls.append(('frequency',v)); self.frequency=v; return True
    def set_tx_power(self,v): self.calls.append(('tx_power',v)); self.tx_power=v; return True
    def set_spreading_factor(self,v): self.calls.append(('sf',v)); self.spreading_factor=v; return True
    def set_bandwidth(self,v): self.calls.append(('bw',v)); self.bandwidth=v; return True
class FakeHandler:
    def __init__(self): self.radio_config={}
    def reload_runtime_config(self): pass
radio=FakeRadio()
cfg={
    'radio': {'frequency':869.618,'bandwidth':62_500,'spreading_factor':8,'coding_rate':8,'tx_power':14},
    'repeater':{}, 'delays':{}
}
daemon=SimpleNamespace(config=cfg,radio=radio,repeater_handler=FakeHandler(),advert_helper=None,dispatcher=None)
mgr=ConfigManager('/tmp/unused.yaml',cfg,daemon)
applied=mgr.live_update_daemon(['radio'])
check(
    applied is True and ('frequency',869) in radio.calls and radio.frequency==869,
    key,'actual-live-application-path',
    f'ConfigManager truncates the stored value to int and applies {radio.frequency} Hz to the radio; calls={radio.calls!r}.'
)

# ---------------------------------------------------------------------------
# advert_interval_minutes is accepted/persisted/exposed but never schedules adverts.
# ---------------------------------------------------------------------------
key='LOCAL-ADVERT-INTERVAL-HAS-NO-RUNTIME-EFFECT'
engine_path=REP/'repeater/engine.py'
api_path=REP/'repeater/web/api_endpoints.py'
engine=engine_path.read_text()
api=api_path.read_text()
check(
    'self.config["repeater"]["advert_interval_minutes"] = mins' in api
    and '"advert_interval_minutes": repeater_config.get("advert_interval_minutes", 120)' in engine
    and 'interval_seconds = self.send_advert_interval_hours * 3600' in engine
    and 'advert_interval_minutes * 60' not in engine,
    key,'static-write-telemetry-scheduler-trace',
    'The API writes and stats expose advert_interval_minutes, while the only periodic advert scheduler uses send_advert_interval_hours.'
)

from repeater.engine import RepeaterHandler
class DummyLock:
    def __enter__(self): return self
    def __exit__(self,*a): return False
class DummyTracker:
    def __init__(self): self.lock=DummyLock(); self.links={}; self.max_entries=512
    def refresh_config(self,cfg): self.refreshed=cfg
    def purge_expired_locked(self,now): pass
    def evict_stalest_locked(self): pass
class ReloadTarget:
    _normalize_multi_acks=staticmethod(RepeaterHandler._normalize_multi_acks)
    reload_runtime_config=RepeaterHandler.reload_runtime_config
    def __init__(self):
        self.config={'repeater': {'send_advert_interval_hours':10,'advert_interval_minutes':1,'cache_ttl':3600,'max_flood_hops':64}, 'delays':{}, 'mesh':{}}
        self.send_advert_interval_hours=10
        self.neighbour_link_tracker=DummyTracker()
        self.loop_detect_mode='off'
    def _normalize_loop_detect_mode(self,m): return str(m)
target=ReloadTarget()
target.reload_runtime_config()
check(
    target.send_advert_interval_hours==10 and hasattr(target.neighbour_link_tracker, 'refreshed'),
    key,'actual-runtime-reload',
    f'After live reload with advert_interval_minutes=1, the active scheduler interval remains {target.send_advert_interval_hours} hours.'
)

# Run the actual background-loop decision for one iteration. A one-minute local
# interval would be due after two minutes, while the active ten-hour field is not.
async def background_countercheck():
    target=SimpleNamespace()
    target.last_noise_measurement=time.time()
    target.noise_floor_interval=30
    target.send_advert_interval_hours=10
    target.send_advert_func=object()
    target.last_advert_time=time.time()-120
    target.last_cache_cleanup=time.time()
    target.last_db_cleanup=time.time()
    target.storage=None
    target.config={'repeater': {'advert_interval_minutes':1,'send_advert_interval_hours':10}}
    target.sent=0
    async def send_advert(): target.sent += 1
    target._send_periodic_advert_async=send_advert
    async def no_noise(): pass
    target._record_noise_floor_async=no_noise
    target._record_crc_errors_async=no_noise
    target.cleanup_cache=lambda: None
    target._background_timer_loop=lambda: RepeaterHandler._background_timer_loop(target)

    original_sleep=asyncio.sleep
    calls=0
    async def stop_after_first(delay):
        nonlocal calls
        calls += 1
        raise asyncio.CancelledError()
    asyncio.sleep=stop_after_first
    try:
        try:
            await RepeaterHandler._background_timer_loop(target)
        except asyncio.CancelledError:
            pass
    finally:
        asyncio.sleep=original_sleep
    return target.sent
sent=asyncio.run(background_countercheck())
check(
    sent==0,
    key,'actual-scheduler-decision',
    'With advert_interval_minutes=1 and last advert two minutes ago, the real scheduler sends nothing because it evaluates the unrelated ten-hour field.'
)


# ---------------------------------------------------------------------------
# Mesh CLI flood advert interval is written to a key the scheduler never reads.
# ---------------------------------------------------------------------------
key='MESHCLI-FLOOD-ADVERT-KEY-MISMATCH'
check(
    'self.repeater_config["flood_advert_interval_hours"] = hours' in mesh
    and 'self.send_advert_interval_hours = config.get("repeater", {}).get(' in engine
    and '"send_advert_interval_hours", 10' in engine,
    key,'static-writer-reader-key-trace',
    'Mesh CLI writes flood_advert_interval_hours, while startup, reload and the timer read send_advert_interval_hours.'
)

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'config.yaml'
    cfg={
        'repeater': {'node_name':'n','name':'n','mode':'forward','send_advert_interval_hours':10},
        'mesh':{}, 'radio':{}, 'security':{}
    }
    mgr=ConfigManager(str(p),cfg)
    cli=MeshCLI(str(p),cfg,mgr)
    reply=cli.handle_command(b'X','set flood.advert.interval 3',True)
    persisted=p.read_text() if p.exists() else ''
    check(
        cfg['repeater'].get('flood_advert_interval_hours')==3
        and cfg['repeater'].get('send_advert_interval_hours')==10
        and 'flood_advert_interval_hours: 3' in persisted,
        key,'real-public-command-persistence',
        f'reply={reply!r}; wrong key persisted as 3 while active scheduler key remains {cfg["repeater"]["send_advert_interval_hours"]}.'
    )

# Reuse the real reload method to prove the persisted wrong key cannot affect runtime.
target=ReloadTarget()
target.config['repeater']['flood_advert_interval_hours']=3
target.config['repeater']['send_advert_interval_hours']=10
target.reload_runtime_config()
check(
    target.send_advert_interval_hours==10,
    key,'actual-runtime-reload-countercheck',
    'The real reload method ignores flood_advert_interval_hours=3 and retains send_advert_interval_hours=10.'
)

print('\nSUMMARY')
from collections import defaultdict
summary=defaultdict(lambda:[0,0])
for k,m,p,d in results:
    summary[k][1]+=1; summary[k][0]+=int(p)
for k,(p,t) in summary.items(): print(f'{k}: {p}/{t}')
if any(not p for _,_,p,_ in results): raise SystemExit(1)
