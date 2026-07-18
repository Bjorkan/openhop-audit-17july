# BUG-034 — Rejected KISS configuration commands still mutate local configuration

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🟠 **Medium** |
| Confidence | **Triple-verified** |
| Area | KISS configuration transaction |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## TL;DR

`send_config_command()` updates the adapter’s local configuration before checking TX-buffer capacity. When the queue is full, it returns `False` but leaves local state changed even though the command never reached the TNC.

## Expected behavior

Local effective state must change only after the command is accepted, and ideally after the device confirms it.

## Required direction

1. Validate and encode first, reserve/enqueue capacity, then commit pending/effective state at the correct acknowledgement boundary.
2. Separate requested, pending, and confirmed modem configuration if the protocol can acknowledge settings.
3. Return an explicit result indicating queued versus confirmed.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | Configuration command ordering | **Passed** | The adapter mutates local configuration before checking whether the command can be queued. |
| Executable reproduction | Full command queue | **Passed** | The real setter returns false while the local value has already changed. |
| Active falsification | Wire-state countercheck | **Passed** | No command frame is emitted while local state reflects the requested value, excluding a hidden successful hardware update. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-034/implementation_plan.md`](../implementation-plans/BUG-034/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/hardware/kiss_serial_wrapper.py` lines 229–272

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/kiss_serial_wrapper.py#L229-L272)

```text
  229 |     def send_config_command(self, cmd: int, value: int) -> bool:
  230 |         """
  231 |         Send KISS configuration command
  232 | 
  233 |         Args:
  234 |             cmd: KISS command type (KISS_CMD_*)
  235 |             value: Command parameter value
  236 | 
  237 |         Returns:
  238 |             True if command sent successfully, False otherwise
  239 |         """
  240 |         if not self.is_connected:
  241 |             return False
  242 | 
  243 |         try:
  244 |             # Update local config
  245 |             if cmd == KISS_CMD_TXDELAY:
  246 |                 self.config["txdelay"] = value
  247 |             elif cmd == KISS_CMD_PERSIST:
  248 |                 self.config["persist"] = value
  249 |             elif cmd == KISS_CMD_SLOTTIME:
  250 |                 self.config["slottime"] = value
  251 |             elif cmd == KISS_CMD_TXTAIL:
  252 |                 self.config["txtail"] = value
  253 |             elif cmd == KISS_CMD_FULLDUP:
  254 |                 self.config["fulldup"] = bool(value)
  255 | 
  256 |             # Create and send KISS command frame
  257 |             kiss_frame = self._encode_kiss_frame(cmd, bytes([value]))
  258 | 
  259 |             if len(self.tx_buffer) < TX_BUFFER_SIZE:
  260 |                 self.tx_buffer.append(kiss_frame)
  261 |                 return True
  262 |             else:
  263 |                 self.stats["buffer_overruns"] += 1
  264 |                 return False
  265 | 
  266 |         except Exception as e:
  267 |             logger.error(f"Failed to send config command: {e}")
  268 |             return False
  269 | 
  270 |     def get_stats(self) -> Dict[str, Any]:
  271 |         """Get interface statistics"""
  272 |         return self.stats.copy()
```

