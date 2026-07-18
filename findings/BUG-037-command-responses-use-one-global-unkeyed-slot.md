# BUG-037 — Companion command responses use one global unkeyed callback slot

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | Companion command correlation |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## TL;DR

Each `send_repeater_command()` replaces one handler-wide response callback. The receive handler does not correlate sender/contact or command instance before satisfying it. An unrelated plain direct message can be swallowed as the response, and overlapping commands can resolve the wrong caller.

## Expected behavior

Command responses must be correlated to the destination and request, and unrelated messages must continue through normal delivery.

## Required direction

1. Maintain pending command requests keyed by expected contact/destination and, if available, a request token.
2. Have `TextMessageHandler` route only messages that match a pending command contract.
3. Remove only the completed/timed-out request instead of clearing global state.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | Global response slot ownership | **Passed** | One callback slot is installed and receive handling has no expected sender or request identity check. |
| Executable reproduction | Unrelated inbound message | **Passed** | An ordinary plain message satisfies the callback and disappears from normal delivery. |
| Active falsification | Overlapping public calls | **Passed** | A response labeled from A completes B while A remains pending, excluding a single-call-only interpretation. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-037/implementation_plan.md`](../implementation-plans/BUG-037/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/companion/base_send.py` lines 1279–1339

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/companion/base_send.py#L1279-L1339)

```text
 1279 |     async def send_repeater_command(
 1280 |         self, pub_key: bytes, command: str, parameters: Optional[str] = None
 1281 |     ) -> dict:
 1282 |         """Send a text-based command to a repeater and wait for the response."""
 1283 |         contact = self.contacts.get_by_key(pub_key)
 1284 |         if not contact:
 1285 |             return {"success": False, "reason": "Contact not found"}
 1286 |         # Resolve by exact public key, not name: two contacts can share a name
 1287 |         # (e.g. a re-keyed node) and get_by_name returns the first match, which
 1288 |         # would encrypt/route to the wrong key.
 1289 |         proxy = self.contacts.get_proxy_by_key(pub_key)
 1290 |         if not proxy:
 1291 |             return {"success": False, "reason": "Contact not found"}
 1292 |         text_handler = self._get_text_handler()
 1293 |         if not text_handler:
 1294 |             return {"success": False, "reason": "Text handler not available"}
 1295 |         full_command = command
 1296 |         if parameters:
 1297 |             full_command += f" {parameters}"
 1298 |         response_data: dict = {"text": None, "success": False}
 1299 |         response_event = asyncio.Event()
 1300 | 
 1301 |         def _response_cb(message_text: str, sender_contact: Any) -> None:
 1302 |             response_data["text"] = message_text
 1303 |             response_data["success"] = True
 1304 |             response_event.set()
 1305 | 
 1306 |         text_handler.set_command_response_callback(_response_cb)
 1307 |         try:
 1308 |             msg_type = "flood" if proxy.out_path_len < 0 else "direct"
 1309 |             pkt, _ = PacketBuilder.create_text_message(
 1310 |                 contact=proxy,
 1311 |                 local_identity=self._identity,
 1312 |                 message=full_command,
 1313 |                 attempt=1,
 1314 |                 message_type=msg_type,
 1315 |                 txt_type=TXT_TYPE_CLI_DATA,
 1316 |             )
 1317 |             self._apply_path_hash_mode(pkt)
 1318 |             await self._send_packet(pkt, wait_for_ack=False)
 1319 |             try:
 1320 |                 await asyncio.wait_for(response_event.wait(), timeout=15.0)
 1321 |             except asyncio.TimeoutError:
 1322 |                 pass
 1323 |             return {
 1324 |                 "success": response_data["success"],
 1325 |                 "repeater": contact.name,
 1326 |                 "command": command,
 1327 |                 "response": response_data["text"],
 1328 |                 "reason": ("Command successful" if response_data["success"] else "No response"),
 1329 |             }
 1330 |         except Exception as e:
 1331 |             logger.error("Repeater command error: %s", e)
 1332 |             return {"success": False, "reason": str(e)}
 1333 |         finally:
 1334 |             text_handler.set_command_response_callback(None)
 1335 | 
 1336 |     def _track_pending_ack(self, ack_crc: int) -> None:
 1337 |         """Record a pending expected ACK with its send time (send_confirmed).
 1338 | 
 1339 |         Bounded circular table (firmware expected_ack_table): when full, the
```
### Evidence 2: `src/openhop_core/node/handlers/text.py` lines 326–354

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/handlers/text.py#L326-L354)

```text
  326 |         # ``sender_prefix`` above, so ``message_body`` is the bare text here.
  327 |         # Firmware treats the body as a C string (BaseChatMesh::onPeerDataRecv):
  328 |         # the visible text ends at the first NUL. Everything after it — the AES
  329 |         # zero padding and, for attempt > 3, the hidden extended-attempt byte —
  330 |         # is not message content and must not be delivered to the app.
  331 |         visible_len = self._text_len(message_body)
  332 |         decoded_msg = message_body[:visible_len].decode("utf-8", "replace")
  333 |         self.log(f"Received TXT_MSG: {decoded_msg}")
  334 | 
  335 |         # Check if this is a command response (if callback is set)
  336 |         if self.command_response_callback:
  337 |             try:
  338 |                 self.command_response_callback(decoded_msg, matched_contact)
  339 |                 self.log(f"Command response captured from {matched_contact.name}: {decoded_msg}")
  340 |                 # Don't save command responses to regular message database
  341 |                 return HandlerResult.consumed()
  342 |             except Exception as e:
  343 |                 self.log(f"Error in command response callback: {e}")
  344 |                 # Continue with normal message processing if callback fails
  345 | 
  346 |         # Save the incoming message by publishing event for app to handle
  347 |         message_timestamp = timestamp_int
  348 | 
  349 |         # Create message event data for the app to handle storage and deduplication
  350 |         normalized_timestamp = (message_timestamp // 1000) * 1000
  351 |         content_hash = (
  352 |             hash(f"{matched_contact.name}_{decoded_msg}_{normalized_timestamp}") & 0xFFFFFFFF
  353 |         )
  354 |         message_id = f"rx_{normalized_timestamp}_{content_hash:08x}"
```

