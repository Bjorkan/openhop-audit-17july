# BUG-038 — Companion login responses use one global completion slot

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | Companion login correlation |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## TL;DR

Login passwords are tracked per destination hash, but completion uses one globally replaced callback. Concurrent logins can resolve the newer request with data from the older peer, and cleanup from an older request can clear the newer callback.

## Expected behavior

Login completion and cleanup must be scoped to the exact destination/request that created the waiter.

## Required direction

1. Replace the global login callback with a pending-request map keyed by destination hash and request generation/token.
2. Dispatch a verified response directly to its matching waiter.
3. Make timeout/cancellation remove only its own entry.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | Login state/callback ownership | **Passed** | Passwords are keyed per target, but login completion uses one global callback slot. |
| Executable reproduction | Overlapping login calls | **Passed** | Response data for A resolves B while A remains pending. |
| Active falsification | Cancellation and cleanup interference | **Passed** | Cleanup of an older login clears the newer waiter, proving no hidden per-operation ownership restores correctness. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-038/implementation_plan.md`](../implementation-plans/BUG-038/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/companion/base_send.py` lines 805–861

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/companion/base_send.py#L805-L861)

```text
  805 |     async def _start_login_request(self, pub_key: bytes, password: str) -> dict:
  806 |         """Start a login request and return SENT metadata plus its result task."""
  807 |         contact = self.contacts.get_by_key(pub_key)
  808 |         if not contact:
  809 |             return {"success": False, "error": "not_found", "reason": "Contact not found"}
  810 |         # Resolve by exact public key, not name: two contacts can share a name
  811 |         # (e.g. a re-keyed node) and get_by_name returns the first match, which
  812 |         # would encrypt/route to the wrong key.
  813 |         proxy = self.contacts.get_proxy_by_key(pub_key)
  814 |         if not proxy:
  815 |             return {"success": False, "error": "not_found", "reason": "Contact not found"}
  816 |         login_handler = self._get_login_response_handler()
  817 |         if not login_handler:
  818 |             return {
  819 |                 "success": False,
  820 |                 "error": "bad_state",
  821 |                 "reason": "Login handler not available",
  822 |             }
  823 |         dest_hash = proxy.dest_hash
  824 |         login_handler.store_login_password(dest_hash, password)
  825 |         login_result: dict = {"success": False, "data": {}}
  826 |         login_event = asyncio.Event()
  827 | 
  828 |         def _login_cb(success: bool, data: dict) -> None:
  829 |             login_result["success"] = success
  830 |             login_result["data"] = data
  831 |             login_event.set()
  832 | 
  833 |         login_handler.set_login_callback(_login_cb)
  834 | 
  835 |         async def _wait_login(timeout_s: float) -> dict:
  836 |             try:
  837 |                 await asyncio.wait_for(login_event.wait(), timeout=timeout_s)
  838 |                 return {"timeout": False}
  839 |             except asyncio.TimeoutError:
  840 |                 return {"timeout": True}
  841 | 
  842 |         def _build_login_packet() -> tuple[Packet, Optional[int]]:
  843 |             return (
  844 |                 PacketBuilder.create_login_packet(
  845 |                     contact=proxy, local_identity=self._identity, password=password
  846 |                 ),
  847 |                 None,
  848 |             )
  849 | 
  850 |         login_sent_tag = int.from_bytes(proxy.public_key_bytes[:4], "little")
  851 | 
  852 |         def _cleanup_login() -> None:
  853 |             login_handler.set_login_callback(None)
  854 |             login_handler.clear_login_password(dest_hash)
  855 | 
  856 |         # MeshCore exposes the first four public-key bytes as the login SENT
  857 |         # tag, rather than the timestamp inside the login packet.
  858 |         login_log_label = f"login -> 0x{dest_hash:02X} ({contact.name})"
  859 |         started = await self._start_request(
  860 |             _build_login_packet,
  861 |             _wait_login,
```
### Evidence 2: `src/openhop_core/node/handlers/login_response.py` lines 36–79

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/handlers/login_response.py#L36-L79)

```text
   36 |         self.local_identity = local_identity
   37 |         self.contacts = contacts
   38 |         self.log = log_fn
   39 |         self.login_callback = login_callback  # Callback to notify of login success/failure
   40 |         # Store login passwords persistently (not tied to contact objects)
   41 |         self._active_login_passwords = {}  # dest_hash -> password
   42 |         # Protocol response handler for forwarding telemetry responses
   43 |         self._protocol_response_handler = None
   44 | 
   45 |     def set_protocol_response_handler(self, protocol_response_handler):
   46 |         """Set protocol response handler for forwarding telemetry responses."""
   47 |         self._protocol_response_handler = protocol_response_handler
   48 | 
   49 |     def set_login_callback(self, callback: Callable[[bool, dict], None]):
   50 |         """Set callback to notify when login response is received.
   51 | 
   52 |         Args:
   53 |             callback: Function that accepts (success: bool, response_data: dict)
   54 |         """
   55 |         self.login_callback = callback
   56 | 
   57 |     def store_login_password(self, dest_hash: int, password: str):
   58 |         """Store password for response decryption by destination hash."""
   59 |         self._active_login_passwords[dest_hash] = password
   60 | 
   61 |     def clear_login_password(self, dest_hash: int):
   62 |         """Clear stored password for destination hash."""
   63 |         if dest_hash in self._active_login_passwords:
   64 |             del self._active_login_passwords[dest_hash]
   65 | 
   66 |     async def __call__(self, packet: Packet) -> HandlerResult:
   67 |         """Handle RESPONSE/ANON_REQ packets and report MAC ownership."""
   68 |         if len(packet.payload) < 4:
   69 |             return HandlerResult.not_for_us()
   70 | 
   71 |         # Determine packet structure: ANON_REQ has our pubkey at bytes 1-33
   72 |         if (
   73 |             len(packet.payload) >= 34
   74 |             and packet.payload[1:33] == self.local_identity.get_public_key()
   75 |         ):
   76 |             # ANON_REQ format: dest_hash(1) + pubkey(32) + encrypted_data
   77 |             dest_hash = packet.payload[0]
   78 |             encrypted_start = 33
   79 |             lookup_hash = dest_hash  # For ANON_REQ, look up by destination hash
```
### Evidence 3: `src/openhop_core/node/handlers/login_response.py` lines 48–56

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/handlers/login_response.py#L48-L56)

```text
   48 | 
   49 |     def set_login_callback(self, callback: Callable[[bool, dict], None]):
   50 |         """Set callback to notify when login response is received.
   51 | 
   52 |         Args:
   53 |             callback: Function that accepts (success: bool, response_data: dict)
   54 |         """
   55 |         self.login_callback = callback
   56 | 
```

