"""Active falsification checks for active BUG-001 through BUG-027.

These checks deliberately search for wrappers, aliases, rollback paths,
normalizers, ownership tokens, locks, fallbacks or documented contracts that
would invalidate or materially narrow the executable reproductions.
"""
from __future__ import annotations

import os
from pathlib import Path

CORE = Path(os.environ["OPENHOP_CORE_ROOT"]).resolve()
REP = Path(os.environ["OPENHOP_REPEATER_ROOT"]).resolve()


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8", errors="replace")


def between(text: str, start: str, end: str) -> str:
    assert start in text, start
    tail = text.split(start, 1)[1]
    return tail.split(end, 1)[0] if end in tail else tail


checks: list[tuple[str, bool, str]] = []


def check(finding: str, condition: bool, detail: str) -> None:
    checks.append((finding, bool(condition), detail))
    print(f"{'PASS' if condition else 'FAIL'} [{finding}] {detail}")


# Shared sources
airtime = read(REP, "repeater/airtime.py")
engine = read(REP, "repeater/engine.py")
config_manager = read(REP, "repeater/config_manager.py")
api = read(REP, "repeater/web/api_endpoints.py")
advert = read(REP, "repeater/handler_helpers/advert.py")
router = read(REP, "repeater/packet_router.py")
storage = read(REP, "repeater/data_acquisition/storage_collector.py")
auth = read(REP, "repeater/web/auth_endpoints.py")
update = read(REP, "repeater/web/update_endpoints.py")
frame_server = read(REP, "repeater/companion/frame_server.py")
openapi = read(REP, "repeater/web/openapi.yaml")
config_example = read(REP, "config.yaml.example")
dispatcher = read(CORE, "src/openhop_core/node/dispatcher.py")
gps = read(REP, "repeater/data_acquisition/gps_service.py")

assets = REP / "repeater/web/html/assets"
system_asset = next(assets.glob("system-*.js")).read_text(errors="replace")
terminal_asset = next(assets.glob("Terminal-*.js")).read_text(errors="replace")
configuration_asset = next(assets.glob("Configuration-*.js")).read_text(errors="replace")

# BUG-001: look for an alternate actual-duty field or consumer conversion.
check(
    "BUG-001",
    "actual_duty_percent" not in airtime + engine + storage + system_asset
    and "utilization_percent" in system_asset
    and "Math.min(g.value/_.value*100,100)" in system_asset,
    "No alternate actual-duty field or UI correction exists; budget utilization is normalized again.",
)

# BUG-003: look for a duty-cycle live-update hook or restart fallback.
live = between(config_manager, "    def live_update_daemon(", "    def update_and_save(")
duty_endpoint = between(api, "    def update_duty_cycle_config(", "    def ")
check(
    "BUG-003",
    "airtime_manager" not in live
    and "max_airtime_per_minute" not in live
    and "restart_required" in duty_endpoint,
    "No AirtimeManager refresh exists in live update; the endpoint still supplies a live-result contract.",
)

# BUG-004: look for any post-radio-change synchronization of cached estimator fields.
calc = between(airtime, "    def calculate_airtime(", "    def ")
apply_radio = between(config_manager, "    def _apply_live_radio_config(", "    def ")
check(
    "BUG-004",
    all(name in calc for name in ("self.spreading_factor", "self.bandwidth", "self.coding_rate", "self.preamble_length"))
    and "airtime_manager" not in apply_radio,
    "Airtime calculation remains bound to cached fields and the live radio path has no estimator synchronization.",
)

# BUG-005: look for a hidden TX-power fallback in the SX1262 configure branch.
branch = between(apply_radio, 'if hasattr(radio, "configure_radio")', '            else:')
check(
    "BUG-005",
    "configure_radio(" in branch and "set_tx_power(" not in branch,
    "The configure_radio capability branch has no fallback call to the separate TX-power setter.",
)

# BUG-006: look for aliases/normalization of the documented threshold keys.
check(
    "BUG-006",
    all(k in config_example + api + configuration_asset for k in ("quiet_max", "normal_max", "busy_max"))
    and all(k not in advert for k in ("quiet_max", "normal_max", "busy_max"))
    and all(f'thresholds.get("{k}"' in advert for k in ("normal", "busy", "congested")),
    "No runtime alias maps the documented/API keys to the three keys read at startup and reload.",
)

# BUG-007: look for response normalization that converts failed save/live results into failure/restart.
advert_endpoint = between(api, "    def update_advert_rate_limit_config(", "    def ")
check(
    "BUG-007",
    "return self._success(" in advert_endpoint
    and '"restart_required": False' in advert_endpoint
    and "applied immediately" in advert_endpoint.lower()
    and 'if not result.get("saved"' not in advert_endpoint,
    "The endpoint itself hard-codes top-level success, no restart and an immediate-success message.",
)

# BUG-008: look for a full-backup import mode or shared allowlist.
import_src = between(api, "    def config_import(", "    def ")
export_src = between(api, "    def config_export(", "    def ")
allow = between(import_src, "ALLOWED_SECTIONS = {", "}")
omitted = ("duty_cycle", "gps", "http", "policy", "sensors", "storage")
check(
    "BUG-008",
    "full backup" in export_src.lower()
    and all(f'"{section}"' not in allow for section in omitted)
    and "full_import" not in import_src,
    "No alternate full-restore path exists for top-level sections exported as part of the backup.",
)

# BUG-009: look for rollback or a success branch gated by both persistence results.
check(
    "BUG-009",
    "update_and_save" in import_src
    and "save_to_file" in import_src
    and '"success": True' in import_src
    and "rollback" not in import_src.lower(),
    "Import contains two persistence attempts but no rollback and still constructs a success response.",
)

# BUG-010: look for staging/deep-copy before mutation or rollback on later validation failure.
radio_endpoint = between(api, "    def update_radio_config(", "    def ")
power_pos = radio_endpoint.find('["tx_power"] =')
bw_error_pos = radio_endpoint.find("Bandwidth must be one of")
check(
    "BUG-010",
    0 <= power_pos < bw_error_pos
    and "deepcopy" not in radio_endpoint.lower()
    and "rollback" not in radio_endpoint.lower(),
    "The shared TX-power field is mutated before later bandwidth rejection, with no staged copy or rollback.",
)

# BUG-011: look for monotonic clocks or protection around GPS realtime correction.
check(
    "BUG-011",
    "time.time()" in airtime
    and "time.monotonic()" not in airtime
    and "clock_settime(time.CLOCK_REALTIME" in gps,
    "The limiter uses mutable wall time and the supplied GPS service can change that same clock.",
)

# BUG-012: look for persistence in quick endpoints or UI-provided correction.
mode_src = between(api, "    def set_mode(", "    def ")
duty_quick = between(api, "    def set_duty_cycle(", "    def ")
check(
    "BUG-012",
    "config_manager" not in mode_src + duty_quick
    and "t.data.persisted=!0" in terminal_asset,
    "Neither quick endpoint persists, and the compiled terminal overrides the returned object to persisted=true.",
)

# BUG-013: look for authenticated-result guards before dedupe commit on PATH/RESPONSE branches.
path_area = between(router, "elif payload_type == PathHandler.payload_type():", "elif payload_type == LoginResponseHandler.payload_type():")
response_area = between(router, "elif payload_type == ProtocolResponseHandler.payload_type():", "elif payload_type == ProtocolRequestHandler.payload_type():")
check(
    "BUG-013",
    "_fan_out_to_bridges" in path_area
    and "_mark_delivered_to_companions" in path_area
    and "_fan_out_to_bridges" in response_area
    and "_mark_delivered_to_companions" in response_area,
    "The affected branches still fan out and then commit delivery independently of the returned authenticated result.",
)

# BUG-014: look for per-candidate exception isolation in the collision helper.
candidates = between(router, "    async def _consume_via_local_candidates(", "    def _record_for_ui(")
check(
    "BUG-014",
    "process_received_packet" in candidates
    and "except" not in candidates,
    "The local-candidate helper has no per-candidate exception handler or continuation fallback.",
)

# BUG-015: look for any conditional use of skip_mqtt in publication.
publish = between(storage, "    def _publish_packet_sync(", "    def ")
check(
    "BUG-015",
    "skip_mqtt" in publish
    and "_publish_packet_to_mqtt" in publish
    and "if skip_mqtt" not in publish
    and "if not skip_mqtt" not in publish,
    "The suppression parameter reaches the method but no branch uses it before MQTT publication.",
)

# BUG-016: compare the capped normal path with the uncapped raw duplicate path.
normal_dupe = between(engine, "        # If this is a duplicate", "        return transmitted")
raw_dupe = between(engine, "    def record_duplicate(", "    def ")
check(
    "BUG-016",
    "max_duplicates_per_packet" in normal_dupe
    and "max_duplicates_per_packet" not in raw_dupe
    and "duplicates\"].append" in raw_dupe,
    "The normal duplicate path enforces the cap; the raw duplicate path appends without it.",
)

# BUG-017: look for a shared parser/bounds application across init and reload.
init = between(engine, "    def __init__(", "    def ")
reload = between(engine, "    def reload_runtime_config(", "    def ")
check(
    "BUG-017",
    'get("cache_ttl", 3600)' in init
    and "max(" in init
    and 'get("cache_ttl", 60)' in reload
    and "max(" not in reload.split("cache_ttl", 1)[1].split("\n", 2)[0],
    "Startup and reload still use different defaults and only startup applies the lower bound.",
)

# BUG-018: look for recursive merge semantics or supplied call sites that would change scope.
update_nested = between(config_manager, "    def update_nested(", "    def ")
call_sites=[]
for path in REP.rglob("*.py"):
    if path.name != "config_manager.py" and "update_nested(" in path.read_text(errors="replace"):
        call_sites.append(path)
check(
    "BUG-018",
    "update_and_save" in update_nested
    and "recursive" not in update_nested.lower()
    and not call_sites,
    "No recursive merge protects siblings; no supplied caller was found, preserving the latent/narrow classification.",
)

# BUG-019: look for request aliases between documented and implemented fields.
duty_endpoint = between(api, "    def update_duty_cycle_config(", "    def ")
check(
    "BUG-019",
    all(field in openapi for field in ("enabled:", "on_time:", "off_time:"))
    and all(field in duty_endpoint for field in ('"max_airtime_percent"', '"enforcement_enabled"'))
    and not any(field in duty_endpoint for field in ('"on_time"', '"off_time"')),
    "No alias/normalizer maps the OpenAPI request fields to the fields parsed by the endpoint.",
)

# BUG-020: look for operation ownership or exclusion of install while checking.
start_install = between(update, "    def start_install(", "    def ")
finish_check = between(update, "    def _finish_check(", "    def ")
check(
    "BUG-020",
    'self.state == "installing"' in start_install
    and 'self.state = "idle"' in finish_check
    and "operation_id" not in start_install + finish_check,
    "Only an existing install is excluded; stale check completion has no job identity and writes idle.",
)

# BUG-021: look for channel/generation ownership at check completion.
set_channel = between(update, "    def set_channel(", "    def ")
check(
    "BUG-021",
    "operation_id" not in set_channel + finish_check
    and "expected_channel" not in finish_check
    and "self.channel" not in finish_check,
    "Check completion has no channel or generation validation capable of discarding a stale result.",
)

# BUG-022: look for persistence result propagation or runtime rollback.
set_channel_endpoint = between(update, "    def set_channel(self, **kwargs):", "    def ")
check(
    "BUG-022",
    "_save_channel" in set_channel
    and "return self._ok(" in set_channel_endpoint
    and "rollback" not in set_channel + set_channel_endpoint,
    "Channel persistence has no propagated failure/rollback before the endpoint reports success.",
)

# BUG-023: look for staged commit or restoration after save failure.
password = between(auth, "    def change_password(", "    def ")
mutation = password.find('["admin_password"] = new_password')
save = password.find("save_to_file")
check(
    "BUG-023",
    0 <= mutation < save
    and "old_password" not in password[save:]
    and "rollback" not in password.lower(),
    "The live password changes before persistence and no failure path restores the prior value.",
)

# BUG-024: look for signature binding or a TypeError-only fallback.
enhanced = between(dispatcher, "    async def _invoke_enhanced_raw_callback(", "    async def ")
check(
    "BUG-024",
    "except Exception" in enhanced
    and "callback(pkt, data)" in enhanced
    and "signature(" not in enhanced
    and "bind(" not in enhanced,
    "Fallback is still triggered by every handler exception rather than pre-bound arity selection.",
)

# BUG-025: look for return-value awaitability handling.
invoke = between(dispatcher, "    async def _invoke_callback(", "    async def ")
check(
    "BUG-025",
    "iscoroutinefunction" in invoke
    and "isawaitable" not in invoke
    and "result =" not in invoke,
    "The helper classifies the callable before invocation and never inspects the returned object.",
)

# BUG-027: look for stable identity, locking or exact removal after the async persistence gap.
persist = between(frame_server, "    async def _persist_companion_message(", "    def _sync_next_from_persistence(")
check(
    "BUG-027",
    "await asyncio.to_thread" in persist
    and "pop_last()" in persist
    and "remove_by" not in persist
    and "lock" not in persist.lower(),
    "Persistence completion still removes queue tail after an await, with no token or lock tying removal to the persisted entry.",
)

failed=[item for item in checks if not item[1]]
print(f"baseline_active_findings={len(checks)} falsification_passed={len(checks)-len(failed)} failed={len(failed)}")
for finding, _, detail in failed:
    print(f"FAILED {finding}: {detail}")
raise SystemExit(bool(failed))
