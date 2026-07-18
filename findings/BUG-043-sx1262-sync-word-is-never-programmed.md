# BUG-043 — Configured SX1262 sync word is never programmed

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | SX1262 hardware configuration |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |

## TL;DR

Repeater parses and passes `sync_word`; `SX1262Radio` stores it, but initialization never calls `setSyncWord`. The bundled low-level `SX126x.setSyncWord()` itself contains no active register write. The radio therefore uses hardware/default state rather than the configured network sync word.

## Hardware-verification boundary

The missing/no-op programming path is proven in source and executable driver-call traces. Actual SX1262 on-air interoperability was not tested on physical hardware and remains hardware-dependent.

## Expected behavior

Initialization and live/reconnect configuration must write the configured sync word to the correct SX126x registers and verify the operation where possible.

## Required direction

1. Implement the correct SX126x sync-word register write in the low-level driver.
2. Call it from `SX1262Radio.begin()` in the correct order before RX starts.
3. Add validation/range normalization and reconnect tests.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | Configuration through SX1262 driver | **Passed** | The sync word is parsed and stored, no wrapper initialization path calls the setter, and the low-level setter’s register write is commented out. |
| Executable reproduction | Low-level driver call | **Passed** | Calling `setSyncWord(0x3444)` performs zero register writes. |
| Active falsification | Full initialization path | **Passed** | Fake-hardware initialization records no sync-word operation; no fallback or alternate setup layer programs it. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-043/implementation_plan.md`](../implementation-plans/BUG-043/implementation_plan.md).

## Source evidence

### Evidence 1: `repeater/config.py` lines 539–551

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config.py#L539-L551)

```text
  539 |             "spreading_factor": radio_config["spreading_factor"],
  540 |             "bandwidth": int(radio_config["bandwidth"]),
  541 |             "coding_rate": radio_config["coding_rate"],
  542 |             "preamble_length": radio_config["preamble_length"],
  543 |             "sync_word": _parse_int(radio_config.get("sync_word", 0x12)),
  544 |         }
  545 | 
  546 |         en_pin = _parse_int(spi_config.get("en_pin"), default=None)
  547 |         en_pins = _parse_int_list(spi_config.get("en_pins"))
  548 |         if en_pin is not None:
  549 |             combined_config["en_pin"] = en_pin
  550 |         if en_pins is not None:
  551 |             combined_config["en_pins"] = en_pins
```
### Evidence 2: `src/openhop_core/hardware/sx1262_wrapper.py` lines 137–153

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/sx1262_wrapper.py#L137-L153)

```text
  137 | 
  138 |         # Radio configuration
  139 |         self.frequency = frequency
  140 |         self.tx_power = tx_power
  141 |         self.spreading_factor = spreading_factor
  142 |         self.bandwidth = bandwidth
  143 |         self.coding_rate = coding_rate
  144 |         self.preamble_length = preamble_length
  145 |         self.sync_word = sync_word
  146 |         self.is_waveshare = is_waveshare
  147 |         self.use_dio3_tcxo = use_dio3_tcxo
  148 |         self.dio3_tcxo_voltage = dio3_tcxo_voltage
  149 |         self.use_dio2_rf = use_dio2_rf
  150 | 
  151 |         # State variables
  152 |         self.lora: Optional[SX126x] = None
  153 |         self.last_rssi: int = -99
```
### Evidence 3: `src/openhop_core/hardware/lora/LoRaRF/SX126x.py` lines 822–838

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/lora/LoRaRF/SX126x.py#L822-L838)

```text
  822 |     def setSyncWord(self, syncWord: int):
  823 |         buf = ((syncWord >> 8) & 0xFF, syncWord & 0xFF)
  824 |         if syncWord <= 0xFF:
  825 |             buf = ((syncWord & 0xF0) | 0x04, (syncWord << 4) | 0x04)
  826 |         # self.writeRegister(self.REG_LORA_SYNC_WORD_MSB, buf, 2)
  827 | 
  828 |     def setFskModulation(self, br: int, pulseShape: int, bandwidth: int, fdev: int):
  829 |         self.setModulationParamsFsk(br, pulseShape, bandwidth, fdev)
  830 | 
  831 |     def setFskPacket(
  832 |         self,
  833 |         preambleLength: int,
  834 |         preambleDetector: int,
  835 |         syncWordLength: int,
  836 |         addrComp: int,
  837 |         packetType: int,
  838 |         payloadLength: int,
```

