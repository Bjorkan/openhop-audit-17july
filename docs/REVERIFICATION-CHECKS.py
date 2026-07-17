from __future__ import annotations

import asyncio
import io
import inspect
import json
import os
import re
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

CORE_ROOT = Path(os.environ['OPENHOP_CORE_ROOT']).resolve()
REPEATER_ROOT = Path(os.environ['OPENHOP_REPEATER_ROOT']).resolve()
sys.path.insert(0, str(CORE_ROOT / 'src'))
sys.path.insert(0, str(REPEATER_ROOT))

import cherrypy

from openhop_core.companion.message_queue import MessageQueue
from openhop_core.companion.models import QueuedMessage
from openhop_core.node.dispatcher import Dispatcher
from openhop_core.node.handlers.path import PathHandler
from openhop_core.protocol.packet_utils import calculate_lora_airtime_ms
from repeater.airtime import AirtimeManager
from repeater.companion.frame_server import CompanionFrameServer
from repeater.config_manager import ConfigManager
from repeater.data_acquisition.storage_collector import StorageCollector
from repeater.engine import RepeaterHandler
from repeater.handler_helpers.advert import AdvertHelper
from repeater.packet_router import PacketRouter
from repeater.web.api_endpoints import APIEndpoints
from repeater.web.auth_endpoints import AuthEndpoints
import repeater.web.update_endpoints as update_mod


def api(config):
    obj = APIEndpoints.__new__(APIEndpoints)
    obj.config = config
    obj.daemon_instance = None
    obj.send_advert_func = None
    obj.event_loop = None
    obj.stats_getter = None
    obj._config_path = '/tmp/reverify-config.yaml'
    obj.config_manager = MagicMock()
    return obj


def request(json_body=None, method='POST', user='admin'):
    cherrypy.request = SimpleNamespace(method=method, params={}, json=json_body or {}, user=user)
    cherrypy.response = SimpleNamespace(headers={}, status=200)


class FakePacket:
    header = 0
    payload = b'\x01payload'
    path = b''
    rssi = -80
    snr = 5.0
    timestamp = 1

    def calculate_packet_hash(self) -> bytes:
        return b'\x01\x02\x03\x04'

    def get_payload_type(self):
        return PathHandler.payload_type()

    def get_path_hashes_hex(self):
        return []

    def get_path_hash_size(self):
        return 1

    def get_raw_length(self):
        return 12


class Bridge:
    def __init__(self, authenticated=False, error=None):
        self.authenticated = authenticated
        self.error = error
        self.calls = 0

    async def process_received_packet(self, packet):
        self.calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(authenticated=self.authenticated)


def make_update_state():
    state = update_mod._UpdateState()
    state.channel = 'main'
    state.current_version = '1.0.0'
    state.latest_version = None
    state.last_checked = None
    state.state = 'idle'
    state.error_message = None
    state.progress_lines = []
    state._install_thread = None
    state.rate_limit_until = None
    return state


def test_bug_001_confirmed_duty_budget_vs_actual_duty_and_ui_double_normalization():
    cfg = {'duty_cycle': {'max_airtime_per_minute': 6000, 'enforcement_enabled': True}, 'radio': {}}
    am = AirtimeManager(cfg)
    am.tx_history = [(100.0, 4572.0)]
    with patch('repeater.airtime.time.time', return_value=100.0):
        stats = am.get_stats()
    assert stats['utilization_percent'] == pytest.approx(76.2)
    assert stats['current_airtime_ms'] / 60000 * 100 == pytest.approx(7.62)
    system_asset = next((REPEATER_ROOT / 'repeater/web/html/assets').glob('system-*.js')).read_text()
    assert 'Math.min(g.value/_.value*100,100)' in system_asset
    assert 'let t=e.utilization_percent' in system_asset


def test_bug_002_retracted_frontend_correctly_unwraps_axios_then_backend_envelope():
    assets = REPEATER_ROOT / 'repeater/web/html/assets'
    api_asset = next(assets.glob('api-*.js')).read_text()
    conf_asset = next(assets.glob('Configuration-*.js')).read_text()
    backend = (REPEATER_ROOT / 'repeater/web/api_endpoints.py').read_text()
    # API helper returns AxiosResponse.data, i.e. the backend envelope.
    assert re.search(r'async post\([^)]*\)\{try\{return\(await \$\.post\([^)]*\)\)\.data\}', api_asset)
    assert 'Va as t' in api_asset
    assert 'result = {"success": True, "data": data}' in backend
    # Radio/duty intentionally extract the envelope's data payload.
    assert 'let n=(await R.post(`/update_radio_config`,t)).data' in conf_asset
    assert 'let e=(await R.post(`/update_duty_cycle_config`' in conf_asset
    # Advert intentionally inspects both envelope success and envelope data.
    assert 't=await R.post(`/update_advert_rate_limit_config`,e),n=t.data;t.success?' in conf_asset


def test_bug_003_confirmed_live_duty_limit_is_cached():
    cfg = {'duty_cycle': {'max_airtime_per_minute': 60000, 'enforcement_enabled': True}, 'radio': {}}
    am = AirtimeManager(cfg)
    cfg['duty_cycle']['max_airtime_per_minute'] = 6000
    with patch('repeater.airtime.time.time', return_value=100.0):
        allowed, _ = am.can_transmit(7000)
    assert am.max_airtime_per_minute == 60000
    assert allowed is True


def test_bug_004_confirmed_live_radio_mutation_does_not_update_airtime_parameters():
    cfg = {'duty_cycle': {'max_airtime_per_minute': 6000}, 'radio': {'spreading_factor': 7, 'bandwidth': 125000, 'coding_rate': 5, 'preamble_length': 8}}
    am = AirtimeManager(cfg)
    old = am.calculate_airtime(50)
    cfg['radio']['spreading_factor'] = 12
    assert am.calculate_airtime(50) == old
    assert calculate_lora_airtime_ms(50, 12, 125000, 5, 8) > old


def test_bug_005_confirmed_configure_radio_branch_omits_tx_power():
    class FakeRadio:
        def __init__(self):
            self.frequency = 1
            self.bandwidth = 2
            self.spreading_factor = 7
            self.coding_rate = 5
            self.tx_power = 2
            self.configure_calls = []
            self.power_calls = []
        def configure_radio(self, **kwargs):
            self.configure_calls.append(kwargs)
            return True
        def set_tx_power(self, power):
            self.power_calls.append(power)
            self.tx_power = power
            return True
    radio = FakeRadio()
    daemon = SimpleNamespace(radio=radio, repeater_handler=SimpleNamespace(radio_config={}), config={})
    cm = ConfigManager('/tmp/unused.yaml', {'radio': {'frequency': 10, 'bandwidth': 125000, 'spreading_factor': 8, 'coding_rate': 8, 'tx_power': 22}}, daemon)
    assert cm._apply_live_radio_config() is True
    assert radio.configure_calls
    assert radio.power_calls == []
    assert radio.tx_power == 2
    sx1262_source = (CORE_ROOT / "src/openhop_core/hardware/sx1262_wrapper.py").read_text()
    configure_block = sx1262_source.split("    def configure_radio(", 1)[1].split("    def get_status", 1)[0]
    assert "tx_power" not in configure_block.split(") -> bool:", 1)[0]
    assert "    def set_tx_power(" in sx1262_source


def test_bug_006_confirmed_ui_threshold_names_are_not_read_by_advert_helper():
    cfg = {'repeater': {'advert_adaptive': {'enabled': True, 'thresholds': {'quiet_max': 0.05, 'normal_max': 0.2, 'busy_max': 0.5}}}}
    ah = AdvertHelper(None, None, config=cfg)
    assert (ah._threshold_normal, ah._threshold_busy, ah._threshold_congested) == (1.0, 5.0, 15.0)


def test_bug_007_confirmed_advert_endpoint_claims_immediate_application_after_failure():
    request({'rate_limit_enabled': True})
    a = api({'repeater': {}})
    a.config_manager.update_and_save.return_value = {'saved': False, 'live_updated': False, 'error': 'disk full'}
    out = a.update_advert_rate_limit_config()
    assert out['success'] is True
    assert out['data']['persisted'] is False
    assert out['data']['live_update'] is False
    assert out['data']['restart_required'] is False
    assert out['data']['message'] == 'Advert rate limit settings applied immediately.'


def test_bug_008_confirmed_exported_top_level_sections_are_skipped_by_import():
    request({'config': {'duty_cycle': {'max_airtime_per_minute': 6000}}})
    a = api({'duty_cycle': {'max_airtime_per_minute': 3600}})
    out = a.config_import()
    assert out['success'] is False
    assert a.config['duty_cycle']['max_airtime_per_minute'] == 3600
    source = inspect.getsource(APIEndpoints.config_import)
    export_source = inspect.getsource(APIEndpoints.config_export)
    assert "full backup that" in export_source and "required for restoring to a new device" in export_source
    assert "from a full backup" in source
    for section in ('duty_cycle', 'policy', 'gps', 'sensors', 'storage', 'http'):
        assert f'"{section}"' not in source.split('ALLOWED_SECTIONS = {', 1)[1].split('}', 1)[0]


def test_bug_009_confirmed_import_ignores_both_persistence_failures():
    request({'config': {'web': {'cors_enabled': True}}})
    a = api({'web': {}})
    a.config_manager.update_and_save.return_value = {'success': False, 'saved': False, 'live_updated': False, 'error': 'disk full'}
    a.config_manager.save_to_file.return_value = False
    out = a.config_import()
    assert out['success'] is True
    assert out['saved'] is False


def test_bug_010_confirmed_invalid_later_field_leaves_earlier_runtime_mutation():
    request({'tx_power': 10, 'bandwidth': 12345})
    a = api({'radio': {'tx_power': 2}, 'delays': {}, 'repeater': {}, 'mesh': {}})
    out = a.update_radio_config()
    assert out['success'] is False
    assert a.config['radio']['tx_power'] == 10
    assert a.config_manager.method_calls == []


def test_bug_011_confirmed_realtime_jump_invalidates_relative_airtime_window():
    cfg = {'duty_cycle': {'max_airtime_per_minute': 6000, 'enforcement_enabled': True}, 'radio': {}}
    am = AirtimeManager(cfg)
    am.tx_history = [(100.0, 6000.0)]
    with patch('repeater.airtime.time.time', return_value=1000.0):
        allowed, _ = am.can_transmit(6000)
    assert allowed is True
    assert am.tx_history == []
    gps_src = (REPEATER_ROOT / 'repeater/data_acquisition/gps_service.py').read_text()
    assert 'time.clock_settime(time.CLOCK_REALTIME, value.timestamp())' in gps_src


def test_bug_012_confirmed_quick_controls_are_unsaved_but_terminal_sets_persisted_true():
    request({'mode': 'monitor'})
    a = api({'repeater': {}})
    mode = a.set_mode()
    request({'enabled': False})
    duty = a.set_duty_cycle()
    assert mode['success'] and duty['success']
    assert a.config_manager.method_calls == []
    terminal = next((REPEATER_ROOT / 'repeater/web/html/assets').glob('Terminal-*.js')).read_text()
    assert 't.data.persisted=!0' in terminal
    assert '/set_mode' in terminal and '/set_duty_cycle' in terminal


@pytest.mark.asyncio
async def test_bug_013_confirmed_path_route_marks_dedupe_after_no_bridge_authentication():
    bridge = Bridge(authenticated=False)
    daemon = SimpleNamespace(
        path_helper=None,
        companion_bridges={1: bridge},
        repeater_handler=None,
        config={},
    )
    router = PacketRouter(daemon)
    packet = FakePacket()
    await router._route_packet(packet)
    assert bridge.calls == 1
    assert router._was_delivered_to_companions(packet) is True


@pytest.mark.asyncio
async def test_bug_013_confirmed_path_route_marks_dedupe_after_bridge_exception():
    bridge = Bridge(error=RuntimeError('bridge failed'))
    daemon = SimpleNamespace(path_helper=None, companion_bridges={1: bridge}, repeater_handler=None, config={})
    router = PacketRouter(daemon)
    packet = FakePacket()
    await router._route_packet(packet)
    assert bridge.calls == 1
    assert router._was_delivered_to_companions(packet) is True


@pytest.mark.asyncio
async def test_bug_014_confirmed_bridge_exception_prevents_colliding_helper_candidate():
    bridge = Bridge(error=RuntimeError('bridge failed'))
    called = False
    async def process(packet):
        nonlocal called
        called = True
        return True
    helper = SimpleNamespace(handlers={1: object()}, process_text_packet=process)
    daemon = SimpleNamespace(companion_bridges={1: bridge}, repeater_handler=None, config={})
    router = PacketRouter(daemon)
    with pytest.raises(RuntimeError):
        await router._consume_via_local_candidates(FakePacket(), {}, 1, helper, 'process_text_packet')
    assert called is False


def test_bug_015_confirmed_skip_mqtt_flag_is_ignored():
    collector = StorageCollector.__new__(StorageCollector)
    collector.websocket_available = False
    collector._publish_to_glass = MagicMock()
    collector._publish_packet_to_mqtt = MagicMock()
    collector._publish_packet_sync({'drop_reason': 'Invalid advert'}, skip_mqtt=True)
    collector._publish_packet_to_mqtt.assert_called_once()


def test_bug_016_confirmed_raw_duplicate_path_bypasses_cap():
    handler = RepeaterHandler.__new__(RepeaterHandler)
    handler.rx_count = 0
    handler.recv_flood_count = 0
    handler.flood_dup_count = 0
    handler.recv_direct_count = 0
    handler.direct_dup_count = 0
    handler.radio_config = {'spreading_factor': 7, 'bandwidth': 125000, 'coding_rate': 5, 'preamble_length': 8}
    handler.neighbour_link_tracker = SimpleNamespace(observe=lambda *a, **k: None)
    handler.storage = None
    handler.max_duplicates_per_packet = 1
    original = {'packet_hash': '01020304', 'duplicates': [{'existing': True}]}
    handler.recent_packets = [original]
    handler._recent_hash_index = {'01020304': original}
    handler._path_hash_display = lambda hashes: None
    handler._packet_record_src_dst = lambda packet, payload_type: (None, None)
    handler._build_packet_record = lambda *a, **k: {'packet_hash': '01020304', 'duplicates': []}
    handler._append_recent_packet = lambda record: handler.recent_packets.append(record)
    handler.record_duplicate(FakePacket(), rssi=-80, snr=5.0)
    assert len(original['duplicates']) == 2


def test_bug_017_confirmed_reload_default_differs_and_drops_missing_cache_ttl_to_60():
    class Tracker:
        def __init__(self):
            self.lock = threading.Lock()
            self.links = {}
            self.max_entries = 100
        def refresh_config(self, config): pass
        def purge_expired_locked(self, now): pass
        def evict_stalest_locked(self): raise AssertionError('not expected')
    target = SimpleNamespace(
        config={'repeater': {}, 'delays': {}, 'mesh': {}},
        cache_ttl=3600,
        neighbour_link_tracker=Tracker(),
        _normalize_multi_acks=lambda config: 0,
        _normalize_loop_detect_mode=lambda value: value,
    )
    RepeaterHandler.reload_runtime_config(target)
    assert target.cache_ttl == 60
    target.config['repeater']['cache_ttl'] = 120
    target.cache_ttl = 300
    RepeaterHandler.reload_runtime_config(target)
    assert target.cache_ttl == 120
    init_src = inspect.getsource(RepeaterHandler.__init__)
    reload_src = inspect.getsource(RepeaterHandler.reload_runtime_config)
    assert 'config.get("repeater", {}).get("cache_ttl", 3600)' in init_src and 'max(' in init_src
    assert 'repeater_config.get("cache_ttl", 60)' in reload_src


def test_bug_018_confirmed_update_nested_clobbers_siblings_but_has_no_repo_call_sites():
    config = {'repeater': {'security': {'admin_password': 'old', 'jwt_secret': 'keep', 'guest_password': 'keep'}}}
    cm = ConfigManager('/tmp/reverify-unused.yaml', config)
    cm.save_to_file = lambda: True
    cm.live_update_daemon = lambda sections: True
    out = cm.update_nested('repeater.security.admin_password', 'new', live_update=False)
    assert out['success'] is True
    assert config['repeater']['security'] == {'admin_password': 'new'}
    call_sites = []
    for path in REPEATER_ROOT.rglob('*.py'):
        if path.name == 'config_manager.py':
            continue
        if 'update_nested(' in path.read_text(errors='ignore'):
            call_sites.append(str(path.relative_to(REPEATER_ROOT)))
    assert call_sites == []


def test_bug_019_confirmed_openapi_duty_schema_mismatch():
    openapi_text = (REPEATER_ROOT / 'repeater/web/openapi.yaml').read_text()
    api_text = (REPEATER_ROOT / 'repeater/web/api_endpoints.py').read_text()
    assert 'on_time:' in openapi_text and 'off_time:' in openapi_text
    assert '"max_airtime_percent"' in api_text and '"enforcement_enabled"' in api_text


def test_bug_020_confirmed_old_check_completion_overwrites_active_install_state():
    state = make_update_state()
    state.state = 'checking'
    with patch.object(update_mod, '_get_installed_version', return_value='1.0.0'):
        started = state.start_install(MagicMock())
        state._finish_check('2.0.0')
    assert started is True
    assert state.state == 'idle'


def test_bug_021_confirmed_old_channel_check_result_attaches_to_new_channel():
    state = make_update_state()
    state.state = 'checking'
    state._save_channel = lambda channel: True
    assert state.channel == 'main'
    state.set_channel('dev')
    with patch.object(update_mod, '_get_installed_version', return_value='1.0.0'):
        state._finish_check('9.9.9-main')
    assert state.channel == 'dev'
    assert state.latest_version == '9.9.9-main'


def test_bug_022_confirmed_channel_save_failure_is_not_propagated():
    state = make_update_state()
    state._save_channel = lambda channel: False
    endpoint = update_mod.UpdateAPIEndpoints()
    cherrypy.request = SimpleNamespace(method='POST', json={'channel': 'dev'})
    cherrypy.response = SimpleNamespace(headers={}, status=200)
    with patch.object(update_mod, '_state', state):
        response = endpoint.set_channel()
    assert response['success'] is True
    assert state.channel == 'dev'


def test_bug_023_confirmed_password_save_failure_leaves_new_runtime_password():
    config = {'repeater': {'security': {'admin_password': 'old-password', 'jwt_secret': 'secret'}}}
    auth = AuthEndpoints(config=config, jwt_handler=MagicMock(), token_manager=MagicMock(), config_manager=SimpleNamespace(save_to_file=lambda: False))
    cherrypy.config.update({'jwt_handler': SimpleNamespace(verify_jwt=lambda token: {'sub': 'admin', 'client_id': 'audit'}), 'token_manager': SimpleNamespace(verify_token=lambda token: None)})
    body = json.dumps({'current_password': 'old-password', 'new_password': 'new-password-123'}).encode()
    cherrypy.request = SimpleNamespace(method='POST', headers={'Authorization': 'Bearer valid'}, body=io.BytesIO(body))
    cherrypy.response = SimpleNamespace(headers={}, status=200)
    response = json.loads(auth.change_password().decode())
    assert response['success'] is False
    assert config['repeater']['security']['admin_password'] == 'new-password-123'


@pytest.mark.asyncio
async def test_bug_024_confirmed_handler_exception_is_misread_as_arity_failure_and_retried():
    dispatcher = Dispatcher.__new__(Dispatcher)
    dispatcher._log = lambda msg: None
    calls = []
    def callback(*args):
        calls.append(len(args))
        if len(args) == 3:
            raise RuntimeError('after side effect')
    await dispatcher._invoke_enhanced_raw_callback(callback, FakePacket(), b'raw', {})
    assert calls == [3, 2]


@pytest.mark.asyncio
async def test_bug_025_confirmed_sync_wrapper_returned_awaitable_is_not_awaited():
    dispatcher = Dispatcher.__new__(Dispatcher)
    ran = False
    coroutines = []
    async def work():
        nonlocal ran
        ran = True
    def callback(packet):
        coro = work()
        coroutines.append(coro)
        return coro
    await dispatcher._invoke_callback(callback, FakePacket())
    assert ran is False
    for coro in coroutines:
        coro.close()


@pytest.mark.asyncio
async def test_former_bug_026_behavior_is_real_but_documented_as_destructive_pop_and_shedding():
    queue = MessageQueue(max_size=4)
    queue.push(QueuedMessage(sender_key=b'a' * 32, text='must survive'))
    server = CompanionFrameServer.__new__(CompanionFrameServer)
    server.bridge = SimpleNamespace(sync_next_message=queue.pop)
    server.sqlite_handler = None
    server._sync_next_from_persistence = lambda: None
    server._build_message_frame = lambda msg: b'encoded-message'
    server._write_queue = asyncio.Queue(maxsize=1)
    server._write_queue.put_nowait(b'already-full')
    await server._cmd_sync_next_message(b'')
    assert queue.count == 0
    assert server._write_queue.qsize() == 1

    # The behavior is undesirable for stronger delivery guarantees, but the
    # supplied contract explicitly calls the operation a pop and the transport
    # explicitly documents QueueFull shedding. That makes it an enhancement,
    # not a defensible confirmed bug without a stronger delivery guarantee.
    docs = (CORE_ROOT / 'docs/docs/companion.md').read_text()
    queue_source = inspect.getsource(MessageQueue.pop)
    transport_source = (CORE_ROOT / 'src/openhop_core/companion/frame_server/transport.py').read_text()
    assert 'CMD_SYNC_NEXT_MESSAGE` | 10 | Pop next queued message' in docs
    assert 'Remove and return the oldest message' in queue_source
    assert 'natural backpressure shedding' in transport_source


@pytest.mark.asyncio
async def test_bug_027_confirmed_persistence_interleaving_pops_newer_message():
    queue = MessageQueue(max_size=4)
    first = QueuedMessage(sender_key=b'a' * 32, text='first')
    second = QueuedMessage(sender_key=b'b' * 32, text='second')
    queue.push(first)
    server = CompanionFrameServer.__new__(CompanionFrameServer)
    server.bridge = SimpleNamespace(message_queue=queue)
    server.companion_hash = 'audit'
    server.sqlite_handler = SimpleNamespace(companion_push_message=lambda *a: True)
    async def fake_to_thread(fn, *args):
        queue.push(second)
        return True
    with patch('repeater.companion.frame_server.asyncio.to_thread', side_effect=fake_to_thread):
        await server._persist_companion_message({'text': 'first'})
    assert queue.count == 1
    assert queue.peek().text == 'first'
