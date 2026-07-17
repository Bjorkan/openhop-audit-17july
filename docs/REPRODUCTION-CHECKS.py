from __future__ import annotations
import json
import tempfile
from pathlib import Path
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

REPEATER_ROOT = Path(os.environ.get("OPENHOP_REPEATER_ROOT", "openhop_repeater")).resolve()
CORE_ROOT = Path(os.environ.get("OPENHOP_CORE_ROOT", "openhop_core")).resolve()
sys.path.insert(0, str(REPEATER_ROOT))
sys.path.insert(0, str(CORE_ROOT / "src"))

import cherrypy

from repeater.airtime import AirtimeManager
from repeater.config_manager import ConfigManager
from repeater.handler_helpers.advert import AdvertHelper
from repeater.web.api_endpoints import APIEndpoints
from openhop_core.protocol.packet_utils import calculate_lora_airtime_ms

RESULTS=[]
def check(name, condition, details):
    RESULTS.append((name, bool(condition), details))
    if not condition:
        raise AssertionError(f"{name}: {details}")

def api(config):
    obj=APIEndpoints.__new__(APIEndpoints)
    obj.config=config
    obj.daemon_instance=None
    obj.send_advert_func=None
    obj.event_loop=None
    obj.stats_getter=None
    obj._config_path='/tmp/test-config.yaml'
    obj.config_manager=MagicMock()
    return obj

def request(json_body=None, method='POST', user='admin'):
    cherrypy.request=SimpleNamespace(method=method, params={}, json=json_body or {}, user=user)
    cherrypy.response=SimpleNamespace(headers={}, status=200)

# 1. Backend utilization is budget usage, not actual duty-cycle percentage.
cfg={'duty_cycle': {'max_airtime_per_minute': 6000, 'enforcement_enabled': True}, 'radio': {}}
am=AirtimeManager(cfg)
am.tx_history=[(100.0,4572.0)]
with patch('repeater.airtime.time.time', return_value=100.0):
    stats=am.get_stats()
actual=stats['current_airtime_ms']/60000*100
check('duty metric semantic mismatch', round(stats['utilization_percent'],1)==76.2 and round(actual,2)==7.62,
      {'reported_utilization_percent':stats['utilization_percent'],'actual_duty_percent':actual,'limit_percent':10.0})

# 2. Duty-cycle limit is cached and does not follow live config mutation.
cfg={'duty_cycle': {'max_airtime_per_minute': 60000, 'enforcement_enabled': True}, 'radio': {}}
am=AirtimeManager(cfg)
cfg['duty_cycle']['max_airtime_per_minute']=6000
with patch('repeater.airtime.time.time', return_value=100.0):
    allowed,_=am.can_transmit(7000)
check('stale live duty limit', am.max_airtime_per_minute==60000 and allowed,
      {'configured_limit_ms':6000,'cached_limit_ms':am.max_airtime_per_minute,'7000ms_allowed':allowed})

# 3. Radio values used for airtime remain stale after live config mutation.
cfg={'duty_cycle': {'max_airtime_per_minute': 6000}, 'radio': {'spreading_factor':7,'bandwidth':125000,'coding_rate':5,'preamble_length':8}}
am=AirtimeManager(cfg)
before=am.calculate_airtime(50)
cfg['radio']['spreading_factor']=12
after=am.calculate_airtime(50)
expected=calculate_lora_airtime_ms(50,12,125000,5,8)
check('stale airtime radio parameters', before==after and expected>after,
      {'cached_airtime_ms':after,'expected_sf12_airtime_ms':expected})

# 4. configure_radio branch never calls set_tx_power for SX1262-like radios.
class FakeRadio:
    def __init__(self):
        self.frequency=1; self.bandwidth=2; self.spreading_factor=7; self.coding_rate=5; self.tx_power=2
        self.configure_calls=[]; self.power_calls=[]
    def configure_radio(self, **kwargs): self.configure_calls.append(kwargs); return True
    def set_tx_power(self, power): self.power_calls.append(power); self.tx_power=power; return True
radio=FakeRadio()
daemon=SimpleNamespace(radio=radio, repeater_handler=SimpleNamespace(radio_config={}), config={})
cm=ConfigManager('/tmp/unused.yaml', {'radio': {'frequency':10,'bandwidth':125000,'spreading_factor':8,'coding_rate':8,'tx_power':22}}, daemon)
ok=cm._apply_live_radio_config()
check('tx power omitted from live configure branch', ok and radio.configure_calls and radio.power_calls==[] and radio.tx_power==2,
      {'configure_calls':radio.configure_calls,'power_calls':radio.power_calls,'runtime_tx_power':radio.tx_power})

# 5. Shipped/UI adaptive threshold keys are ignored by AdvertHelper.
cfg={'repeater': {'advert_adaptive': {'enabled': True, 'thresholds': {'quiet_max':0.05,'normal_max':0.2,'busy_max':0.5}}}}
ah=AdvertHelper(None, None, config=cfg)
check('adaptive threshold key mismatch', (ah._threshold_normal,ah._threshold_busy,ah._threshold_congested)==(1.0,5.0,15.0),
      {'configured':cfg['repeater']['advert_adaptive']['thresholds'],'runtime':[ah._threshold_normal,ah._threshold_busy,ah._threshold_congested]})

# 6. Advert endpoint returns success even when persistence/live update failed.
request({'rate_limit_enabled':True})
a=api({'repeater':{}})
a.config_manager.update_and_save.return_value={'saved':False,'live_updated':False,'error':'disk full'}
out=a.update_advert_rate_limit_config()
check('advert update false success', out['success'] is True and out['data']['persisted'] is False and out['data']['restart_required'] is False,
      out)

# 7. A full export contains sections that config_import refuses.
request({'config': {'duty_cycle': {'max_airtime_per_minute':6000}}})
a=api({'duty_cycle': {'max_airtime_per_minute':3600}})
out=a.config_import()
check('config import omits exported sections', out['success'] is False and a.config['duty_cycle']['max_airtime_per_minute']==3600,
      out)

# 8. config_import reports success when both saves fail.
request({'config': {'web': {'cors_enabled':True}}})
a=api({'web': {}})
a.config_manager.update_and_save.return_value={'success':False,'saved':False,'live_updated':False,'error':'disk full'}
a.config_manager.save_to_file.return_value=False
out=a.config_import()
check('config import false success', out['success'] is True and out['saved'] is False,
      out)

# 9. A rejected multi-field request leaves earlier values mutated in memory.
request({'tx_power':10,'bandwidth':12345})
a=api({'radio': {'tx_power':2}, 'delays':{}, 'repeater':{}, 'mesh':{}})
out=a.update_radio_config()
check('partial mutation on validation failure', out['success'] is False and a.config['radio']['tx_power']==10,
      {'response':out,'radio_config':a.config['radio']})

# 10. Forward wall-clock jump empties the rolling airtime history immediately.
cfg={'duty_cycle': {'max_airtime_per_minute':6000,'enforcement_enabled':True}, 'radio':{}}
am=AirtimeManager(cfg)
am.tx_history=[(100.0,6000.0)]
with patch('repeater.airtime.time.time', return_value=1000.0):
    allowed,_=am.can_transmit(6000)
check('wall clock jump resets airtime window', allowed and am.tx_history==[],
      {'allowed_after_clock_jump':allowed,'remaining_history':am.tx_history})

# 11. Quick endpoints mutate memory but never invoke persistence.
request({'mode':'monitor'})
a=api({'repeater':{}})
out=a.set_mode()
mode_calls=a.config_manager.method_calls
request({'enabled':False})
out2=a.set_duty_cycle()
check('quick controls are not persisted', out['success'] and out2['success'] and mode_calls==[] and a.config_manager.method_calls==[],
      {'mode_response':out,'duty_response':out2,'config_manager_calls':a.config_manager.method_calls})

# 12. Compiled UI contains incompatible handling of the standard success envelope.
assets=REPEATER_ROOT/'repeater/web/html/assets'
conf=(assets/'Configuration-gqXY-Aef.js').read_text(errors='ignore')
api_src=(REPEATER_ROOT/'repeater/web/api_endpoints.py').read_text()
patterns=[
    'let n=(await R.post(`/update_radio_config`,t)).data;if(n.message||n.persisted)',
    'let e=(await R.post(`/update_duty_cycle_config`,{max_airtime_percent:h.value,enforcement_enabled:g.value})).data;e?.message||e?.persisted',
    't=await R.post(`/update_advert_rate_limit_config`,e),n=t.data;t.success?'
]
check('UI response-envelope mismatch', 'result = {"success": True, "data": data}' in api_src and all(p in conf for p in patterns),
      {'bad_patterns_found':sum(p in conf for p in patterns)})

for name,ok,details in RESULTS:
    print(f"PASS: {name}\n  {json.dumps(details, default=str, sort_keys=True)}")
print(f"\n{len(RESULTS)} focused checks passed")
