from __future__ import annotations

import asyncio
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path

CORE = Path('/mnt/data/deep_audit_round2/core/openhop_core-fix-all-the-things-core')
REP = Path('/mnt/data/deep_audit_round2/repeater/openhop_repeater-fix-all-the-things')
sys.path.insert(0, str(CORE / 'src'))
sys.path.insert(0, str(REP))

from openhop_core.companion import CompanionBridge
from openhop_core.companion.frame_server.server import CompanionFrameServer
from openhop_core.companion.models import Contact
from openhop_core.node.handlers.text import TextMessageHandler
from openhop_core.protocol import LocalIdentity, PacketBuilder
from openhop_core.protocol.constants import TXT_TYPE_PLAIN
from repeater.companion.bridge import RepeaterCompanionBridge


@dataclass
class Result:
    finding: str
    check: str
    passed: bool
    detail: str

results: list[Result] = []

def record(finding: str, check: str, passed: bool, detail: str) -> None:
    results.append(Result(finding, check, passed, detail))
    status = 'PASS' if passed else 'FAIL'
    print(f'[{status}] {finding} / {check}: {detail}')


async def validate_command_response_global_slot() -> None:
    fid = 'GLOBAL-COMMAND-RESPONSE-SLOT'
    import openhop_core.companion.base_send as base_send
    import openhop_core.node.handlers.text as text_mod

    send_src = inspect.getsource(base_send._SendOpsMixin.send_repeater_command)
    text_src = inspect.getsource(text_mod.TextMessageHandler.__call__)
    passed = (
        'set_command_response_callback(_response_cb)' in send_src
        and 'set_command_response_callback(None)' in send_src
        and 'if self.command_response_callback:' in text_src
        and 'txt_type' not in text_src[text_src.index('if self.command_response_callback:'):text_src.index("# Save the incoming message")]
    )
    record(fid, 'static-unkeyed-slot', passed,
           'A single handler-wide callback is installed; the receive branch has no expected sender or CLI_DATA check.')

    # Dynamic wrong-message check through the real encrypted text handler.
    receiver = LocalIdentity()
    sender = LocalIdentity()

    class Contacts:
        def __init__(self, contact): self.contacts = [contact]
    contact = type('C', (), {
        'public_key': sender.get_public_key(), 'name': 'wrong-sender',
        'out_path_len': -1, 'out_path': b'', 'sync_since': 0,
    })()
    event_calls: list[tuple] = []
    class Events:
        def publish_sync(self, *args): event_calls.append(args)
    handler = TextMessageHandler(receiver, Contacts(contact), lambda *_: None,
                                 lambda *_args, **_kwargs: asyncio.sleep(0), Events())
    captured: list[tuple[str, object]] = []
    handler.set_command_response_callback(lambda text, who: captured.append((text, who)))
    recv_contact = type('RC', (), {'public_key': receiver.get_public_key().hex(), 'out_path': b'', 'out_path_len': -1})()
    packet, _ = PacketBuilder.create_text_message(
        recv_contact, sender, 'ordinary personal message', attempt=1,
        message_type='direct', txt_type=TXT_TYPE_PLAIN,
    )
    outcome = await handler(packet)
    passed = bool(captured and captured[0][0] == 'ordinary personal message' and not event_calls and outcome.consumed)
    record(fid, 'dynamic-unrelated-plain-message', passed,
           'An ordinary TXT_TYPE_PLAIN message from a contact satisfies the command callback and is omitted from normal delivery.')

    # Public API concurrency: two command calls, then a response from contact A resolves B.
    sent = []
    async def inject(pkt, wait_for_ack=False):
        sent.append(pkt)
        return True
    bridge = CompanionBridge(LocalIdentity(), inject)
    peer_a = LocalIdentity(); peer_b = LocalIdentity()
    ca = Contact(public_key=peer_a.get_public_key(), name='A', out_path_len=-1)
    cb = Contact(public_key=peer_b.get_public_key(), name='B', out_path_len=-1)
    assert bridge.contacts.add(ca) and bridge.contacts.add(cb)
    task_a = asyncio.create_task(bridge.send_repeater_command(ca.public_key, 'status'))
    await asyncio.sleep(0)
    task_b = asyncio.create_task(bridge.send_repeater_command(cb.public_key, 'status'))
    await asyncio.sleep(0)
    current_cb = bridge._get_text_handler().command_response_callback
    current_cb('response-from-A', ca)
    result_b = await asyncio.wait_for(task_b, 1.0)
    a_pending = not task_a.done()
    task_a.cancel()
    try:
        await task_a
    except BaseException:
        pass
    passed = (
        result_b.get('success') is True
        and result_b.get('repeater') == 'B'
        and result_b.get('response') == 'response-from-A'
        and a_pending
    )
    record(fid, 'public-api-overlap-misroutes-response', passed,
           'The second public command call completes as B using a response explicitly supplied from A; A remains pending.')


async def validate_login_global_slot() -> None:
    fid = 'GLOBAL-LOGIN-RESPONSE-SLOT'
    import openhop_core.companion.base_send as base_send
    import openhop_core.node.handlers.login_response as login_mod
    start_src = inspect.getsource(base_send._SendOpsMixin._start_login_request)
    handler_src = inspect.getsource(login_mod.LoginResponseHandler)
    passed = (
        'set_login_callback(_login_cb)' in start_src
        and 'set_login_callback(None)' in start_src
        and 'self.login_callback = callback' in handler_src
        and '_active_login_passwords' in handler_src
    )
    record(fid, 'static-global-callback-vs-keyed-passwords', passed,
           'Passwords are keyed by destination hash, but completion is routed through one global callback replaced by every request.')

    sent = []
    async def inject(pkt, wait_for_ack=False): sent.append(pkt); return True
    bridge = CompanionBridge(LocalIdentity(), inject)
    peer_a = LocalIdentity(); peer_b = LocalIdentity()
    ca = Contact(public_key=peer_a.get_public_key(), name='A', out_path_len=-1)
    cb = Contact(public_key=peer_b.get_public_key(), name='B', out_path_len=-1)
    assert bridge.contacts.add(ca) and bridge.contacts.add(cb)
    start_a = await bridge._start_login_request(ca.public_key, 'pw-a')
    start_b = await bridge._start_login_request(cb.public_key, 'pw-b')
    login_handler = bridge._get_login_response_handler()
    # The active callback belongs to B. Feed data labelled as A and it resolves B.
    login_handler.login_callback(True, {
        'timestamp': 111, 'is_admin': True, 'keep_alive_interval': 2,
        'reserved': 7, 'firmware_ver_level': 3, 'contact': ca,
    })
    result_b = await asyncio.wait_for(start_b['task'], 1.0)
    a_pending = not start_a['task'].done()
    passed = (
        result_b.get('success') is True
        and result_b.get('repeater') == 'B'
        and result_b.get('tag') == 111
        and a_pending
    )
    record(fid, 'dynamic-overlap-misroutes-login-result', passed,
           'The active B request completes using callback data supplied for A, while A remains pending.')

    # Cleanup from the older request can clear the callback for the newer request.
    # Cancel A: its request cleanup runs and globally sets callback to None.
    start_a['task'].cancel()
    try:
        await start_a['task']
    except BaseException:
        pass
    await asyncio.sleep(0)
    callback_cleared = login_handler.login_callback is None
    # B already completed above; make a fresh overlapping pair to demonstrate cleanup interference before response.
    before_c = set(bridge._background_tasks)
    start_c = await bridge._start_login_request(ca.public_key, 'pw-c')
    added_c = set(bridge._background_tasks) - before_c
    raw_c = next(t for t in added_c if t is not start_c['task'])
    start_d = await bridge._start_login_request(cb.public_key, 'pw-d')
    await asyncio.sleep(0.05)
    raw_c.cancel()
    try:
        await raw_c
    except BaseException:
        pass
    await asyncio.sleep(0)
    cleared_newer = login_handler.login_callback is None
    for t in list(bridge._background_tasks):
        t.cancel()
    await asyncio.gather(*list(bridge._background_tasks), return_exceptions=True)
    passed = cleared_newer
    record(fid, 'older-cleanup-clears-newer-waiter', passed,
           'Cleanup from an older login request globally removes the callback installed by the newer request.')


async def validate_frame_server_callback_clear() -> None:
    fid = 'FRAME-SERVER-CLEARS-EXTERNAL-PUSH-CALLBACKS'
    import openhop_core.companion.frame_server.push as push_mod
    src = inspect.getsource(push_mod._PushMixin._setup_push_callbacks)
    passed = 'self.bridge.clear_push_callbacks()' in src
    record(fid, 'static-clear-all-before-register', passed,
           'Every frame-client setup calls the bridge-wide clear_push_callbacks rather than removing only the prior frame-server listeners.')

    async def inject(pkt, wait_for_ack=False): return True
    bridge = CompanionBridge(LocalIdentity(), inject)
    external_calls = []
    bridge.on_message_event(lambda event: external_calls.append(event))
    server = CompanionFrameServer(bridge=bridge, companion_hash='aa', port=0)
    before = list(bridge._push_callbacks['message_event'])
    server._setup_push_callbacks()
    after = list(bridge._push_callbacks['message_event'])
    passed = len(before) == 1 and before[0] not in after and server._on_message_event in after
    record(fid, 'dynamic-registration-removes-third-party-listener', passed,
           'A pre-existing external listener is removed immediately when the frame server installs its callbacks.')

    # Simulate an endpoint registering once, then a later frame-client connection.
    endpoint_calls = []
    endpoint_cb = lambda event: endpoint_calls.append(event)
    bridge.on_message_event(endpoint_cb)
    # A later client connection invokes this same setup path.
    server._setup_push_callbacks()
    class E: pass
    event = E(); event.sender_key=b''; event.text='x'; event.timestamp=0; event.txt_type=0
    event.path_len=0; event.packet_hash=b''; event.snr=0; event.rssi=0; event.sender_prefix=b''; event.queued=False
    # Fire through the real bridge callback dispatcher.
    await bridge._fire_callbacks('message_event', event)
    passed = endpoint_calls == [] and endpoint_cb not in bridge._push_callbacks['message_event']
    record(fid, 'runtime-reconnect-silences-once-registered-consumer', passed,
           'After the frame-server reconnect setup, the external once-registered consumer receives no subsequent event.')


async def validate_prefs_false_success() -> None:
    fid = 'COMPANION-PREFS-PERSISTENCE-FALSE-SUCCESS'
    import repeater.companion.bridge as bridge_mod
    src = inspect.getsource(bridge_mod.RepeaterCompanionBridge._save_prefs)
    passed = 'companion_save_prefs' in src and 'if not self._sqlite_handler.companion_save_prefs' not in src
    record(fid, 'static-return-value-discarded', passed,
           'The SQLite persistence method returns bool, but _save_prefs discards it and exposes no failure to setters.')

    class DB:
        def __init__(self, stored=None, mode='false'):
            self.stored = stored or {'node_name': 'persisted-old'}
            self.mode = mode
            self.save_calls = 0
        def companion_save_prefs(self, key, prefs):
            self.save_calls += 1
            if self.mode == 'raise': raise OSError('disk full')
            if self.mode == 'false': return False
            self.stored = dict(prefs); return True
        def companion_load_prefs(self, key): return dict(self.stored)
    async def inject(pkt, wait_for_ack=False): return True
    db = DB(mode='false')
    bridge = RepeaterCompanionBridge(LocalIdentity(), inject, node_name='persisted-old',
                                     sqlite_handler=db, companion_hash='aa')
    bridge.set_advert_name('runtime-new')
    passed = bridge.prefs.node_name == 'runtime-new' and db.stored['node_name'] == 'persisted-old' and db.save_calls == 1
    record(fid, 'dynamic-setter-reports-no-error-after-failed-save', passed,
           'The public setter returns normally and mutates runtime state although persistence explicitly returned False.')

    # Restart equivalence: the new bridge restores the old persisted value.
    restarted = RepeaterCompanionBridge(LocalIdentity(), inject, node_name='bootstrap',
                                        sqlite_handler=db, companion_hash='aa')
    restarted._load_prefs()
    passed = restarted.prefs.node_name == 'persisted-old' and bridge.prefs.node_name == 'runtime-new'
    record(fid, 'restart-reverts-successfully-returned-change', passed,
           'A fresh bridge loads the old persisted value, proving the accepted runtime change is lost on restart.')


async def main() -> None:
    await validate_command_response_global_slot()
    await validate_login_global_slot()
    await validate_frame_server_callback_clear()
    await validate_prefs_false_success()
    print('\nSUMMARY')
    grouped: dict[str, list[Result]] = {}
    for r in results: grouped.setdefault(r.finding, []).append(r)
    for finding, checks in grouped.items():
        print(f'{finding}: {sum(c.passed for c in checks)}/{len(checks)}')
    failures = [r for r in results if not r.passed]
    if failures:
        raise SystemExit(1)

if __name__ == '__main__':
    asyncio.run(main())
