# BUG-030 — Unterminated KISS receive frames can grow memory without bound

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | KISS parser / memory safety |
| Components | OpenHop Core |
| Audit date | 2026-07-17 |

## TL;DR

`MAX_FRAME_SIZE` constrains transmitted frames, but neither receive decoder enforces it. A stream that starts a KISS frame and never terminates it continuously appends to `rx_frame_buffer`, allowing malformed input or a noisy serial link to consume unbounded memory.

## Expected behavior

Receive parsing must cap frame size, increment an error metric, discard/resynchronize safely, and continue processing subsequent valid frames.

## Required direction

1. Enforce a receive-frame bound in the shared byte-processing path used by both decoder entry points.
2. On overflow, increment a dedicated/error counter, clear parser state, and wait for the next frame delimiter.
3. Keep escaped-byte and port-command parsing correct after resynchronization.

## Triple verification

| Method | Check | Result | Observation |
|---:|---|---|---|
| 1 | Bytewise decoder | **Passed** | A frame reached 10,240 bytes with a configured maximum of 512. |
| 2 | Bulk decoder | **Passed** | One chunk produced a 51,200-byte receive buffer. |
| 3 | Worker-like stream | **Passed** | Repeated 4 KiB chunks grew the buffer to 131,072 bytes without a terminator. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition.

## Implementation plan

See [`implementation-plans/BUG-030/implementation_plan.md`](../implementation-plans/BUG-030/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/hardware/kiss_serial_wrapper.py` lines 36–47

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/kiss_serial_wrapper.py#L36-L47)

```text
   36 | KISS_CMD_FULLDUP = 0x05
   37 | KISS_CMD_VENDOR = 0x06
   38 | KISS_CMD_RETURN = 0xFF
   39 | 
   40 | # Buffer and timing constants
   41 | MAX_FRAME_SIZE = 512
   42 | RX_BUFFER_SIZE = 1024
   43 | TX_BUFFER_SIZE = 1024
   44 | DEFAULT_BAUDRATE = 115200
   45 | DEFAULT_TIMEOUT = 1.0
   46 | # RX worker uses a short blocking read so it sleeps in the kernel (releasing the GIL)
   47 | # instead of busy-polling. Actual port timeout is min(this, self.timeout).
```
### Evidence 2: `src/openhop_core/hardware/kiss_serial_wrapper.py` lines 593–632

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/kiss_serial_wrapper.py#L593-L632)

```text
  593 | 
  594 |     def _decode_kiss_byte(self, byte: int):
  595 |         """
  596 |         Process received byte for KISS frame decoding
  597 | 
  598 |         Args:
  599 |             byte: Received byte
  600 |         """
  601 |         if byte == KISS_FEND:
  602 |             if self.in_frame and len(self.rx_frame_buffer) > 1:
  603 |                 # Complete frame received
  604 |                 self._process_received_frame()
  605 |             # Start new frame
  606 |             self.rx_frame_buffer.clear()
  607 |             self.in_frame = True
  608 |             self.escaped = False
  609 | 
  610 |         elif byte == KISS_FESC:
  611 |             if self.in_frame:
  612 |                 self.escaped = True
  613 | 
  614 |         elif self.escaped:
  615 |             if byte == KISS_TFEND:
  616 |                 self.rx_frame_buffer.append(KISS_FEND)
  617 |             elif byte == KISS_TFESC:
  618 |                 self.rx_frame_buffer.append(KISS_FESC)
  619 |             else:
  620 |                 # Invalid escape sequence
  621 |                 self.stats["frame_errors"] += 1
  622 |                 logger.warning(f"Invalid KISS escape sequence: 0x{byte:02X}")
  623 |             self.escaped = False
  624 | 
  625 |         else:
  626 |             if self.in_frame:
  627 |                 self.rx_frame_buffer.append(byte)
  628 | 
  629 |     def _decode_kiss(self, data: bytes) -> None:
  630 |         """Bulk KISS decoder used by the RX worker.
  631 | 
  632 |         Behaviorally identical to feeding each byte through ``_decode_kiss_byte``, but
```
### Evidence 3: `src/openhop_core/hardware/kiss_serial_wrapper.py` lines 628–677

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/kiss_serial_wrapper.py#L628-L677)

```text
  628 | 
  629 |     def _decode_kiss(self, data: bytes) -> None:
  630 |         """Bulk KISS decoder used by the RX worker.
  631 | 
  632 |         Behaviorally identical to feeding each byte through ``_decode_kiss_byte``, but
  633 |         copies runs of plain bytes with C-level ``bytes.find``/slicing and only does
  634 |         per-byte work at FEND/FESC. This cuts Python-level work (and GIL hold time) under
  635 |         bursty traffic so the reader keeps draining the port. Frame state persists on self
  636 |         across calls, so frames spanning multiple read chunks decode correctly.
  637 |         """
  638 |         n = len(data)
  639 |         if n == 0:
  640 |             return
  641 | 
  642 |         buf = self.rx_frame_buffer  # bytearray, mutated in place
  643 |         in_frame = self.in_frame
  644 |         escaped = self.escaped
  645 |         i = 0
  646 | 
  647 |         while i < n:
  648 |             if escaped:
  649 |                 b = data[i]
  650 |                 i += 1
  651 |                 escaped = False
  652 |                 if b == KISS_TFEND:
  653 |                     buf.append(KISS_FEND)
  654 |                 elif b == KISS_TFESC:
  655 |                     buf.append(KISS_FESC)
  656 |                 else:
  657 |                     # Mirrors _decode_kiss_byte: count + log, but do NOT clear/resync
  658 |                     self.stats["frame_errors"] += 1
  659 |                     logger.warning(f"Invalid KISS escape sequence: 0x{b:02X}")
  660 |                 continue
  661 | 
  662 |             fend = data.find(_KISS_FEND_B, i)
  663 |             fesc = data.find(_KISS_FESC_B, i)
  664 |             if fend == -1:
  665 |                 nxt = fesc
  666 |             elif fesc == -1:
  667 |                 nxt = fend
  668 |             else:
  669 |                 nxt = fend if fend < fesc else fesc
  670 | 
  671 |             run_end = n if nxt == -1 else nxt
  672 |             if run_end > i and in_frame:
  673 |                 buf += data[i:run_end]  # this decoder applies no MAX_FRAME_SIZE cap
  674 | 
  675 |             if nxt == -1:
  676 |                 break
  677 | 
```

