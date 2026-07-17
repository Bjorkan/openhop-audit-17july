from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

REPEATER_ROOT = Path(os.environ.get("OPENHOP_REPEATER_ROOT", "openhop_repeater")).resolve()
CORE_ROOT = Path(os.environ.get("OPENHOP_CORE_ROOT", "openhop_core")).resolve()
sys.path.insert(0, str(REPEATER_ROOT))
sys.path.insert(0, str(CORE_ROOT / "src"))

import cherrypy

from openhop_core.companion.message_queue import MessageQueue
from openhop_core.companion.models import QueuedMessage
from openhop_core.node.dispatcher import Dispatcher
from repeater.companion.frame_server import CompanionFrameServer
from repeater.config_manager import ConfigManager
from repeater.data_acquisition.storage_collector import StorageCollector
from repeater.engine import RepeaterHandler
from repeater.packet_router import PacketRouter
from repeater.web.auth_endpoints import AuthEndpoints
import repeater.web.update_endpoints as update_mod

RESULTS: list[tuple[str, bool, object]] = []


def check(name: str, condition: bool, details: object) -> None:
    RESULTS.append((name, bool(condition), details))
    if not condition:
        raise AssertionError(f"{name}: {details}")


class FakePacket:
    header = 0
    payload = b"\x01payload"
    path = b""

    def calculate_packet_hash(self) -> bytes:
        return b"\x01\x02\x03\x04"

    def get_path_hashes_hex(self):
        return []

    def get_path_hash_size(self):
        return 1

    def get_raw_length(self):
        return 12


class ResultBridge:
    def __init__(self, authenticated: bool = False, error: Exception | None = None):
        self.authenticated = authenticated
        self.error = error
        self.calls = 0

    async def process_received_packet(self, packet):
        self.calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(authenticated=self.authenticated)


def make_update_state() -> update_mod._UpdateState:
    state = update_mod._UpdateState.__new__(update_mod._UpdateState)
    state._lock = threading.Lock()
    state.current_version = "1.0.0"
    state.latest_version = None
    state.has_update = False
    state.channel = "main"
    state.last_checked = None
    state.state = "idle"
    state.error_message = None
    state.progress_lines = []
    state._install_thread = None
    state.rate_limit_until = None
    return state


async def check_companion_delivery_marked_after_failure() -> tuple[bool, dict]:
    router = PacketRouter(SimpleNamespace())
    packet = FakePacket()
    bridge = ResultBridge(authenticated=False)
    authenticated = await router._fan_out_to_bridges(packet, {1: bridge}, context="audit")
    # This is what the PATH and protocol-response branches currently do.
    router._mark_delivered_to_companions(packet)
    return (
        not authenticated and router._was_delivered_to_companions(packet),
        {
            "bridge_authenticated": authenticated,
            "marked_delivered": router._was_delivered_to_companions(packet),
            "bridge_calls": bridge.calls,
        },
    )


ok, details = asyncio.run(check_companion_delivery_marked_after_failure())
check("failed companion delivery is still deduplicated", ok, details)


async def check_collision_exception_shadows_other_identity() -> tuple[bool, dict]:
    bad_bridge = ResultBridge(error=RuntimeError("bridge failure"))
    helper = SimpleNamespace(handlers={1: object()}, called=False)

    async def process(packet):
        helper.called = True
        return True

    helper.process_text_packet = process
    daemon = SimpleNamespace(
        companion_bridges={1: bad_bridge},
        repeater_handler=None,
        config={},
    )
    router = PacketRouter(daemon)
    raised = None
    try:
        await router._consume_via_local_candidates(
            FakePacket(), {}, 1, helper, "process_text_packet"
        )
    except Exception as exc:  # expected current behaviour
        raised = type(exc).__name__
    return (
        raised == "RuntimeError" and helper.called is False,
        {"raised": raised, "other_local_candidate_called": helper.called},
    )


ok, details = asyncio.run(check_collision_exception_shadows_other_identity())
check("companion exception blocks colliding local identity", ok, details)

# Invalid packet MQTT suppression flag is accepted and passed through, but ignored.
collector = StorageCollector.__new__(StorageCollector)
collector.websocket_available = False
collector._publish_to_glass = MagicMock()
collector._publish_packet_to_mqtt = MagicMock()
collector._publish_packet_sync({"drop_reason": "Invalid advert"}, skip_mqtt=True)
check(
    "invalid packet MQTT suppression flag is ignored",
    collector._publish_packet_to_mqtt.call_count == 1,
    {
        "skip_mqtt_argument": True,
        "mqtt_publish_calls": collector._publish_packet_to_mqtt.call_count,
    },
)

# The raw duplicate path appends past the explicit max_duplicates_per_packet cap.
handler = RepeaterHandler.__new__(RepeaterHandler)
handler.rx_count = 0
handler.recv_flood_count = 0
handler.flood_dup_count = 0
handler.recv_direct_count = 0
handler.direct_dup_count = 0
handler.radio_config = {
    "spreading_factor": 7,
    "bandwidth": 125000,
    "coding_rate": 5,
    "preamble_length": 8,
}
handler.neighbour_link_tracker = SimpleNamespace(observe=lambda *a, **k: None)
handler.storage = None
handler.max_duplicates_per_packet = 1
original = {"packet_hash": "01020304", "duplicates": [{"existing": True}]}
handler.recent_packets = [original]
handler._recent_hash_index = {"01020304": original}
handler._path_hash_display = lambda hashes: None
handler._packet_record_src_dst = lambda packet, payload_type: (None, None)
handler._build_packet_record = lambda *a, **k: {
    "packet_hash": "01020304",
    "duplicates": [],
}
handler._append_recent_packet = lambda record: handler.recent_packets.append(record)
handler.record_duplicate(FakePacket(), rssi=-80, snr=5.0)
check(
    "raw duplicate path bypasses duplicate cap",
    len(original["duplicates"]) == 2,
    {"configured_cap": 1, "duplicates_after_record": len(original["duplicates"])},
)

# Startup and reload use different cache TTL defaults and constraints.
class FakeNeighbourTracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.links = {}
        self.max_entries = 100

    def refresh_config(self, config):
        return None

    def purge_expired_locked(self, now):
        return None

    def evict_stalest_locked(self):
        raise AssertionError("nothing to evict")


reload_target = SimpleNamespace(
    config={"repeater": {}, "delays": {}, "mesh": {}},
    cache_ttl=3600,
    neighbour_link_tracker=FakeNeighbourTracker(),
    _normalize_multi_acks=lambda config: 0,
    _normalize_loop_detect_mode=lambda value: value,
)
RepeaterHandler.reload_runtime_config(reload_target)
check(
    "runtime reload silently changes cache TTL",
    reload_target.cache_ttl == 60,
    {"before_reload": 3600, "after_reload": reload_target.cache_ttl},
)

# Deep update helper replaces the whole second-level mapping.
config = {
    "repeater": {
        "security": {
            "admin_password": "old-password",
            "jwt_secret": "keep-me",
            "guest_password": "keep-me-too",
        }
    }
}
cm = ConfigManager("/tmp/audit-unused.yaml", config)
cm.save_to_file = lambda: True
cm.live_update_daemon = lambda sections: True
result = cm.update_nested("repeater.security.admin_password", "new-password", live_update=False)
check(
    "deep update helper clobbers sibling configuration",
    result["success"] is True
    and config["repeater"]["security"] == {"admin_password": "new-password"},
    {"security_after_update": config["repeater"]["security"]},
)

# Published OpenAPI request fields do not match the implemented endpoint.
openapi_text = (REPEATER_ROOT / "repeater/web/openapi.yaml").read_text(errors="replace")
api_text = (REPEATER_ROOT / "repeater/web/api_endpoints.py").read_text(errors="replace")
check(
    "OpenAPI duty-cycle contract is stale",
    all(key in openapi_text for key in ("on_time:", "off_time:"))
    and all(key in api_text for key in ('"max_airtime_percent"', '"enforcement_enabled"')),
    {
        "documented_fields": ["enabled", "on_time", "off_time"],
        "implemented_fields": ["max_airtime_percent", "enforcement_enabled"],
    },
)

# Install can replace a running version check, and the old check can then reset state to idle.
state = make_update_state()
state.state = "checking"
with patch.object(update_mod, "_get_installed_version", return_value="1.0.0"):
    started = state.start_install(MagicMock())
    state._finish_check("2.0.0")
check(
    "version check completion overwrites active install state",
    started is True and state.state == "idle",
    {"install_started_from_checking": started, "state_after_old_check_finished": state.state},
)

# A check result captured for one channel is attached to whichever channel is current later.
state = make_update_state()
state.state = "checking"
checked_channel = state.channel
state._save_channel = lambda channel: True
state.set_channel("dev")
with patch.object(update_mod, "_get_installed_version", return_value="1.0.0"):
    state._finish_check("9.9.9-main")
check(
    "stale update result is attached to a new channel",
    checked_channel == "main"
    and state.channel == "dev"
    and state.latest_version == "9.9.9-main",
    {
        "checked_channel": checked_channel,
        "reported_channel": state.channel,
        "reported_latest": state.latest_version,
    },
)

# Channel persistence has no success result; the HTTP endpoint reports success regardless.
state = make_update_state()
state._save_channel = lambda channel: False
endpoint = update_mod.UpdateAPIEndpoints()
cherrypy.request = SimpleNamespace(method="POST", json={"channel": "dev"})
cherrypy.response = SimpleNamespace(headers={}, status=200)
with patch.object(update_mod, "_state", state):
    response = endpoint.set_channel()
check(
    "channel endpoint reports success after persistence failure",
    response["success"] is True and state.channel == "dev",
    {"response": response, "runtime_channel": state.channel, "persisted": False},
)

# Password is changed in memory before save, and failure does not restore it.
config = {
    "repeater": {
        "security": {
            "admin_password": "old-password",
            "jwt_secret": "secret",
        }
    }
}
auth = AuthEndpoints(
    config=config,
    jwt_handler=MagicMock(),
    token_manager=MagicMock(),
    config_manager=SimpleNamespace(save_to_file=lambda: False),
)
cherrypy.config.update(
    {
        "jwt_handler": SimpleNamespace(
            verify_jwt=lambda token: {"sub": "admin", "client_id": "audit"}
        ),
        "token_manager": SimpleNamespace(verify_token=lambda token: None),
    }
)
body = json.dumps(
    {"current_password": "old-password", "new_password": "new-password-123"}
).encode("utf-8")
cherrypy.request = SimpleNamespace(
    method="POST",
    headers={"Authorization": "Bearer valid"},
    body=io.BytesIO(body),
)
cherrypy.response = SimpleNamespace(headers={}, status=200)
password_response = json.loads(auth.change_password().decode("utf-8"))
check(
    "failed password save leaves new runtime password active",
    password_response["success"] is False
    and config["repeater"]["security"]["admin_password"] == "new-password-123",
    {
        "response": password_response,
        "runtime_password_changed": True,
        "response_status": cherrypy.response.status,
    },
)

# Any exception from the enhanced callback is treated as signature mismatch and triggers a second call.
async def run_double_callback() -> tuple[int, list[str]]:
    dispatcher = Dispatcher.__new__(Dispatcher)
    logs: list[str] = []
    dispatcher._log = logs.append
    calls = 0

    def callback(*args):
        nonlocal calls
        calls += 1
        if len(args) == 3:
            raise RuntimeError("handler failed after side effect")

    await dispatcher._invoke_enhanced_raw_callback(callback, FakePacket(), b"raw", {})
    return calls, logs


calls, logs = asyncio.run(run_double_callback())
check(
    "enhanced raw callback is retried after internal failure",
    calls == 2,
    {"callback_calls": calls, "logs": logs},
)

# A normal callable returning an awaitable is not awaited.
async def run_sync_wrapper_callback() -> tuple[bool, int]:
    dispatcher = Dispatcher.__new__(Dispatcher)
    ran = False
    returned = []

    async def work():
        nonlocal ran
        ran = True

    def callback(packet):
        coro = work()
        returned.append(coro)
        return coro

    await dispatcher._invoke_callback(callback, FakePacket())
    before_cleanup = ran
    for coro in returned:
        coro.close()
    return before_cleanup, len(returned)


ran, returned_count = asyncio.run(run_sync_wrapper_callback())
check(
    "awaitable returned by sync callback wrapper is ignored",
    ran is False and returned_count == 1,
    {"callback_coroutines_created": returned_count, "callback_body_ran": ran},
)

# Queue entry is popped before frame enqueue; QueueFull drops the only copy.
async def run_destructive_sync() -> tuple[int, int]:
    queue = MessageQueue(max_size=4)
    queue.push(QueuedMessage(sender_key=b"a" * 32, text="must survive"))
    server = CompanionFrameServer.__new__(CompanionFrameServer)
    server.bridge = SimpleNamespace(sync_next_message=queue.pop)
    server.sqlite_handler = None
    server._sync_next_from_persistence = lambda: None
    server._build_message_frame = lambda msg: b"encoded-message"
    server._write_queue = asyncio.Queue(maxsize=1)
    server._write_queue.put_nowait(b"already-full")
    await server._cmd_sync_next_message(b"")
    return queue.count, server._write_queue.qsize()


remaining_messages, outbound_queue_size = asyncio.run(run_destructive_sync())
check(
    "companion message is removed before outbound enqueue succeeds",
    remaining_messages == 0 and outbound_queue_size == 1,
    {
        "messages_remaining": remaining_messages,
        "outbound_queue_size": outbound_queue_size,
        "message_frame_enqueued": False,
    },
)

# Await during persistence allows another push; pop_last then removes the wrong message.
async def run_wrong_pop_last() -> tuple[str | None, int]:
    queue = MessageQueue(max_size=4)
    first = QueuedMessage(sender_key=b"a" * 32, text="first")
    second = QueuedMessage(sender_key=b"b" * 32, text="second")
    queue.push(first)
    server = CompanionFrameServer.__new__(CompanionFrameServer)
    server.bridge = SimpleNamespace(message_queue=queue)
    server.companion_hash = "audit"
    server.sqlite_handler = SimpleNamespace(companion_push_message=lambda *a: True)

    async def fake_to_thread(fn, *args):
        queue.push(second)
        return True

    with patch("repeater.companion.frame_server.asyncio.to_thread", side_effect=fake_to_thread):
        await server._persist_companion_message({"text": "first"})
    remaining = queue.peek()
    return (remaining.text if remaining else None), queue.count


remaining_text, remaining_count = asyncio.run(run_wrong_pop_last())
check(
    "async persistence can pop a newer unpersisted message",
    remaining_text == "first" and remaining_count == 1,
    {"message_remaining_in_memory": remaining_text, "queue_count": remaining_count},
)

for name, ok, details in RESULTS:
    print(f"PASS: {name}\n  {json.dumps(details, default=str, sort_keys=True)}")
print(f"\n{len(RESULTS)} deeper focused checks passed")
