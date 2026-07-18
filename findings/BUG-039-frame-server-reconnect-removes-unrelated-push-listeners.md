# BUG-039 — Frame-server callback setup removes unrelated bridge listeners

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | Companion callback lifecycle |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |

## TL;DR

Every frame-server setup invokes bridge-wide `clear_push_callbacks()`, which clears all registered listeners, not only callbacks owned by the prior frame-server client. A reconnect can therefore silently disable separately registered Repeater/API consumers.

## Expected behavior

A component must unregister only callbacks it owns; reconnecting one client must not mutate third-party subscriptions.

## Required direction

1. Return registration handles/tokens from callback registration and remove by handle.
2. Have `CompanionFrameServer` retain and replace only its own registrations.
3. Make reconnect setup idempotent without global clearing.

## Triple verification

| Method | Check | Result | Observation |
|---:|---|---|---|
| 1 | Static clear-all trace | **Passed** | Frame setup calls a bridge-wide clear before registering. |
| 2 | Third-party listener | **Passed** | An existing listener is removed immediately. |
| 3 | Reconnect path | **Passed** | A once-registered external consumer receives no later event after setup runs again. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition.

## Implementation plan

See [`implementation-plans/BUG-039/implementation_plan.md`](../implementation-plans/BUG-039/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/companion/frame_server/push.py` lines 36–70

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/companion/frame_server/push.py#L36-L70)

```text
   36 |     def _setup_push_callbacks(self) -> None:
   37 |         """Subscribe to bridge events and send PUSH frames to connected client."""
   38 |         # Clear any callbacks registered by a previous connection so they
   39 |         # don't accumulate across reconnections.
   40 |         self.bridge.clear_push_callbacks()
   41 |         self.bridge.on_message_event(self._on_message_event)
   42 |         self.bridge.on_channel_message_event(self._on_channel_message_event)
   43 |         self.bridge.on_channel_data_event(self._on_channel_data_event)
   44 |         self.bridge.on_send_confirmed(self._on_send_confirmed)
   45 |         self.bridge.on_advert_received(self._on_advert_received)
   46 |         self.bridge.on_node_discovered(self._on_node_discovered)
   47 |         self.bridge.on_contact_path_updated(self._on_contact_path_updated)
   48 |         self.bridge.on_binary_response(self._on_binary_response)
   49 |         self.bridge.on_path_discovery_response(self._on_path_discovery_response)
   50 |         self.bridge.on_contact_deleted(self._on_contact_deleted)
   51 |         self.bridge.on_contacts_full(self._on_contacts_full)
   52 |         self.bridge.on_raw_data_received(self._on_raw_data_received)
   53 | 
   54 |     # -------------------------------------------------------------------------
   55 |     # Bridge event callbacks (registered by _setup_push_callbacks)
   56 |     # -------------------------------------------------------------------------
   57 | 
   58 |     async def _on_message_event(self, event: MessageEvent):
   59 |         msg_dict = {
   60 |             "sender_key": event.sender_key,
   61 |             "text": event.text,
   62 |             "timestamp": event.timestamp,
   63 |             "txt_type": event.txt_type,
   64 |             "is_channel": False,
   65 |             "channel_idx": 0,
   66 |             "path_len": event.path_len,
   67 |             "packet_hash": event.packet_hash,
   68 |             "snr": event.snr,
   69 |             "rssi": event.rssi,
   70 |             "sender_prefix": event.sender_prefix,
```
### Evidence 2: `src/openhop_core/companion/base_callbacks.py` lines 23–38

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/companion/base_callbacks.py#L23-L38)

```text
   23 |     def clear_push_callbacks(self) -> None:
   24 |         """Remove all registered push callbacks.
   25 | 
   26 |         Called by FrameServer between client connections so that stale
   27 |         closures from a previous connection are not invoked on the next one.
   28 |         """
   29 |         for key in self._push_callbacks:
   30 |             self._push_callbacks[key].clear()
   31 | 
   32 |     def on_message_event(self, callback: Callable) -> None:
   33 |         """Register a direct-message callback receiving one ``MessageEvent``."""
   34 |         self._push_callbacks["message_event"].append(callback)
   35 | 
   36 |     def on_channel_message_event(self, callback: Callable) -> None:
   37 |         """Register a channel-text callback receiving one ``ChannelMessageEvent``."""
   38 |         self._push_callbacks["channel_message_event"].append(callback)
```

