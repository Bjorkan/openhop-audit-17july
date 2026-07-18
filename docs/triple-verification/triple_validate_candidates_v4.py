import asyncio
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

CORE = Path(os.environ["OPENHOP_CORE_ROOT"]).resolve()
REP = Path(os.environ["OPENHOP_REPEATER_ROOT"]).resolve()
sys.path.insert(0,str(CORE/'src'))
sys.path.insert(0,str(REP))

results=[]
def ok(key,method,detail):
    results.append((key,method,True,detail)); print(f'PASS [{key}] {method}: {detail}')
def fail(key,method,detail):
    results.append((key,method,False,detail)); print(f'FAIL [{key}] {method}: {detail}')

def check(cond,key,method,detail):
    (ok if cond else fail)(key,method,detail)

# ---------------------------------------------------------------------------
# SX1262 sync word is accepted/configured but never written to hardware.
# ---------------------------------------------------------------------------
key='SX1262-SYNC-WORD-NOT-PROGRAMMED'
wrapper=(CORE/'src/openhop_core/hardware/sx1262_wrapper.py').read_text()
low=(CORE/'src/openhop_core/hardware/lora/LoRaRF/SX126x.py').read_text()
rep_cfg=(REP/'repeater/config.py').read_text()
check(
    'self.sync_word = sync_word' in wrapper
    and '"sync_word": _parse_int(radio_config.get("sync_word", 0x12))' in rep_cfg
    and 'self.lora.setSyncWord' not in wrapper,
    key,'static-config-to-driver-trace',
    'Repeater passes sync_word into SX1262Radio and the wrapper stores it, but no wrapper path calls setSyncWord.'
)

from openhop_core.hardware.lora.LoRaRF.SX126x import SX126x
obj=SX126x.__new__(SX126x)
writes=[]
obj.writeRegister=lambda *args,**kwargs: writes.append((args,kwargs))
obj.setSyncWord(0x3444)
check(writes==[],key,'direct-low-level-runtime',f'setSyncWord(0x3444) produced register_writes={writes}')

# Full wrapper initialization with fake hardware: verify every hardware call.
import openhop_core.hardware.sx1262_wrapper as sw
class FakeGPIO:
    def setup_interrupt_pin(self,*a,**k): return object()
    def setup_output_pin(self,*a,**k): return True
    def blink_led(self,*a,**k): pass
    def write_pin(self,*a,**k): return True
    def cleanup_pin(self,*a,**k): pass
    def cleanup_all(self,*a,**k): pass
class FakeLoRa:
    STANDBY_RC=1; LORA_MODEM=2; REGULATOR_DC_DC=3
    CAL_IMG_430=10; CAL_IMG_440=11; CAL_IMG_470=12; CAL_IMG_510=13; CAL_IMG_779=14; CAL_IMG_787=15; CAL_IMG_863=16; CAL_IMG_870=17; CAL_IMG_902=18; CAL_IMG_928=19
    TX_POWER_SX1262=20; HEADER_EXPLICIT=21; CRC_ON=22; IQ_STANDARD=23; IRQ_NONE=0; RX_CONTINUOUS=0xffffff; RX_GAIN_BOOSTED=1
    DIO3_OUTPUT_1_6=1; DIO3_OUTPUT_1_7=2; DIO3_OUTPUT_1_8=3; DIO3_OUTPUT_2_2=4; DIO3_OUTPUT_2_4=5; DIO3_OUTPUT_2_7=6; DIO3_OUTPUT_3_0=7; DIO3_OUTPUT_3_3=8
    IRQ_RX_DONE=1; IRQ_CRC_ERR=2; IRQ_TIMEOUT=4; IRQ_HEADER_ERR=8; IRQ_PREAMBLE_DETECTED=16; IRQ_SYNC_WORD_VALID=32; IRQ_HEADER_VALID=64; IRQ_TX_DONE=128; IRQ_CAD_DETECTED=256; IRQ_CAD_DONE=512
    def __init__(self): self.calls=[]
    def __getattr__(self,n):
        if n.startswith('IRQ_') or n.isupper(): return 0
        def f(*a,**k): self.calls.append((n,a,k)); return 0
        return f
    def busyCheck(self): self.calls.append(('busyCheck',(),{})); return False
    def getDeviceErrors(self): return 0
fakegpio=FakeGPIO()
sw.GPIOPinManager=lambda *a,**k: fakegpio
sw.set_gpio_manager=lambda mgr: None
sw.SX126x=FakeLoRa
sw.SX1262Radio._active_instance=None
radio=sw.SX1262Radio(sync_word=0x3444, txen_pin=-1, rxen_pin=-1, radio_timing_delay=0)
radio._gpio_manager=fakegpio
began=radio.begin()
call_names=[c[0] for c in radio.lora.calls]
check(
    began is True and not any('sync' in n.lower() for n in call_names),
    key,'full-wrapper-initialization',
    f'begin={began}; hardware calls={call_names}; no sync-word operation was issued despite configured 0x3444.'
)
radio.cleanup()

# ---------------------------------------------------------------------------
# MeshCLI consumes ConfigManager.save_to_file() using an obsolete tuple contract.
# ---------------------------------------------------------------------------
key='MESHCLI-SAVE-RETURN-CONTRACT-MISMATCH'
mesh=(REP/'repeater/handler_helpers/mesh_cli.py').read_text()
cm=(REP/'repeater/config_manager.py').read_text()
check(
    'def save_to_file(self) -> bool:' in cm
    and mesh.count('saved, _ = self.config_manager.save_to_file()') >= 20
    and 'saved, err = self.config_manager.save_to_file()' in mesh,
    key,'static-signature-and-callsite-trace',
    f'ConfigManager returns bool; MeshCLI contains {mesh.count("saved, _ = self.config_manager.save_to_file()") + mesh.count("saved, err = self.config_manager.save_to_file()") } tuple-unpack call sites.'
)

from repeater.config_manager import ConfigManager
from repeater.handler_helpers.mesh_cli import MeshCLI
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'config.yaml'
    cfg={'repeater': {'node_name':'before','name':'before','mode':'forward'}, 'mesh':{}, 'radio':{}, 'security':{}}
    mgr=ConfigManager(str(p),cfg)
    cli=MeshCLI(str(p),cfg,mgr)
    reply=cli.handle_command(b'X','set name after',True)
    persisted=p.read_text() if p.exists() else ''
    check(
        reply.startswith('Error:') and 'cannot unpack non-iterable bool object' in reply and 'after' in persisted,
        key,'real-config-manager-public-command',
        f'reply={reply!r}; persisted_contains_after={"after" in persisted}; live update was skipped after the successful write.'
    )

# Existing tests provide a tuple, proving they validate a different runtime contract.
tests=(REP/'tests/test_handler_helpers_mesh_cli.py').read_text()
check(
    'save_to_file=MagicMock(return_value=(save_ok, err))' in tests
    and 'save_to_file(self) -> bool' in cm,
    key,'test-double-countercheck',
    'MeshCLI tests mock the obsolete tuple return while the production ConfigManager returns bool, explaining why the regression suite passes.'
)

# ---------------------------------------------------------------------------
# MeshCLI security commands use a different config subtree from authentication.
# ---------------------------------------------------------------------------
key='MESHCLI-SECURITY-WRITES-WRONG-CONFIG-SUBTREE'
login=(REP/'repeater/handler_helpers/login.py').read_text()
example=(REP/'config.yaml.example').read_text()
check(
    'self.config["security"]["password"] = new_password' in mesh
    and 'self.config["security"]["guest_password"] = value' in mesh
    and 'security = config.get("repeater", {}).get("security", {})' in login,
    key,'static-writer-reader-path-mismatch',
    'MeshCLI writes top-level security.password/guest_password; login reads repeater.security.admin_password/guest_password.'
)

# Dynamic check uses a tuple-compatible manager only to isolate the path mismatch.
class TupleMgr:
    def __init__(self): self.live=[]
    def save_to_file(self): return (True,None)
    def live_update_daemon(self,sections): self.live.append(sections); return True
cfg={
    'repeater': {'node_name':'n','name':'n','security': {'admin_password':'old-admin','guest_password':'old-guest'}},
    'mesh':{},'radio':{},'security':{}
}
cli=MeshCLI('/tmp/unused.yaml',cfg,TupleMgr())
r1=cli.handle_command(b'X','password new-admin',True)
r2=cli.handle_command(b'X','set guest.password new-guest',True)
check(
    r1.startswith('password now:') and r2=='OK'
    and cfg['repeater']['security']=={'admin_password':'old-admin','guest_password':'old-guest'}
    and cfg['security'].get('password')=='new-admin'
    and cfg['security'].get('guest_password')=='new-guest',
    key,'dynamic-command-state-separation',
    f'CLI replies=({r1!r},{r2!r}); authentication subtree remains {cfg["repeater"]["security"]!r}.'
)

# Instantiate the actual login helper after the CLI writes and verify the ACL still uses the old nested credentials.
from repeater.handler_helpers.login import LoginHelper
class FakeIdentity:
    def get_public_key(self): return bytes([0x42])+b'X'*31
helper=LoginHelper(identity_manager=SimpleNamespace(), config=cfg)
helper.register_identity('n', FakeIdentity(), identity_type='repeater', config=cfg)
acl=helper.acls[0x42]
check(
    acl.admin_password=='old-admin' and acl.guest_password=='old-guest',
    key,'actual-login-helper-countercheck',
    f'LoginHelper built ACL credentials admin={acl.admin_password!r}, guest={acl.guest_password!r} after CLI claimed the new values were accepted.'
)

# ---------------------------------------------------------------------------
# MQTT restart candidate is intentionally tested as a counterexample; no current
# internal path reuses the same object after StorageCollector.close().
# ---------------------------------------------------------------------------
key='MQTT-HEARTBEAT-RESTART-CANDIDATE'
storage=(REP/'repeater/data_acquisition/storage_collector.py').read_text()
check(
    storage.count('self.mqtt_handler.connect()')==1 and 'self.mqtt_handler.disconnect()' in storage,
    key,'runtime-reachability-countercheck',
    'StorageCollector constructs/connects once and disconnects only during close; no in-repo restart of the same publisher object was found. Candidate must not be reported as an active bug.'
)

print('\nSUMMARY')
from collections import defaultdict
s=defaultdict(lambda:[0,0])
for k,m,p,d in results:
    s[k][1]+=1; s[k][0]+=int(p)
for k,(p,t) in s.items(): print(f'{k}: {p}/{t}')
if any(not p for _,_,p,_ in results): raise SystemExit(1)
