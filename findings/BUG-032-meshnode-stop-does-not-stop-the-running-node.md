# BUG-032 — `MeshNode.stop()` does not stop a running node

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🟠 **Medium** |
| Confidence | **Triple-verified** |
| Area | Lifecycle / shutdown |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## TL;DR

`MeshNode.start()` awaits `Dispatcher.run_forever()`. `MeshNode.stop()` only logs and does not signal, cancel, or await that loop, so callers cannot stop a node through its public lifecycle API.

## Expected behavior

After `await node.stop()`, the task created by `node.start()` must terminate and radio/background resources must be closed deterministically.

## Required direction

1. Add an explicit dispatcher stop event/cancellation contract and have `MeshNode.stop()` invoke and await it.
2. Make start/stop idempotent and define restart support.
3. Close or sleep the radio and cancel owned background tasks during shutdown.

## Triple verification

| Method | Check | Result | Observation |
|---:|---|---|---|
| 1 | Static lifecycle trace | **Passed** | Start awaits an infinite dispatcher loop; stop only logs. |
| 2 | Public stop call | **Passed** | A blocking dispatcher remains active after `await node.stop()`. |
| 3 | Real dispatcher loop | **Passed** | The actual `run_forever` task remains pending after stop. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition.

## Implementation plan

See [`implementation-plans/BUG-032/implementation_plan.md`](../implementation-plans/BUG-032/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/node/node.py` lines 86–108

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/node.py#L86-L108)

```text
   86 |     # -------------------------------------------------------------------------
   87 | 
   88 |     async def start(self) -> None:
   89 |         """Start the mesh node and begin processing radio communications.
   90 | 
   91 |         Enters the dispatcher's main event loop for handling incoming/outgoing
   92 |         messages.  This method blocks until the node is stopped.
   93 |         """
   94 |         await self.dispatcher.run_forever()
   95 | 
   96 |     def stop(self):
   97 |         """Stop the mesh node and clean up associated services."""
   98 |         try:
   99 |             self.logger.info("Node stopped")
  100 |         except Exception as e:
  101 |             self.logger.error(f"Error stopping node: {e}")
  102 | 
  103 |     # -------------------------------------------------------------------------
  104 |     # Transport
  105 |     # -------------------------------------------------------------------------
  106 | 
  107 |     async def send_packet(self, pkt: Any, *, wait_for_ack: bool = False, **kwargs) -> bool:
  108 |         """Send a raw packet via the dispatcher.
```
### Evidence 2: `src/openhop_core/node/dispatcher.py` lines 735–766

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/node/dispatcher.py#L735-L766)

```text
  735 | 
  736 |     async def run_forever(self) -> None:
  737 |         """Run the dispatcher maintenance loop indefinitely (call this in an asyncio task)."""
  738 |         health_check_counter = 0
  739 |         while True:
  740 |             # Clean out old ACK CRCs (older than 5 seconds)
  741 |             now = asyncio.get_running_loop().time()
  742 |             self._recent_acks = {crc: ts for crc, ts in self._recent_acks.items() if now - ts < 5}
  743 | 
  744 |             # Clean old packet hashes for deduplication
  745 |             self.packet_filter.cleanup_old_hashes()
  746 | 
  747 |             # Simple health check every 60 seconds
  748 |             health_check_counter += 1
  749 |             if health_check_counter >= 60:
  750 |                 health_check_counter = 0
  751 |                 if hasattr(self.radio, "check_radio_health"):
  752 |                     await asyncio.to_thread(self.radio.check_radio_health)
  753 | 
  754 |             # With callback-based RX, just do maintenance tasks
  755 |             await asyncio.sleep(1.0)  # Check every second for cleanup
  756 | 
  757 |     # ------------------------------------------------------------------
  758 |     # Internal helper methods
  759 |     # ------------------------------------------------------------------
  760 | 
  761 |     async def _rx_once(self) -> None:
  762 |         """Fallback RX method for radios that don't support callbacks."""
  763 |         try:
  764 |             data = await self.radio.wait_for_rx()
  765 |         except Exception as err:
  766 |             self._log(f"Radio RX error: {err}")
```

