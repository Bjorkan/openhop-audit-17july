# POSSIBLE-ENHANCEMENT-005 — Possible enhancement — define a radio capability adapter instead of `hasattr` branches

[← Audit index](../README.md)

> Reverification verdict: **Factual premise confirmed; implementation remains optional.**

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Hardware abstraction |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

Live configuration depends on introspection and wrapper-specific side effects.

## What happens now

`ConfigManager` branches on `configure_radio`, `set_frequency`, `set_tx_power`, `radio_config`, and other optional attributes. Different wrappers apply different subsets.

## Expected behaviour / proposed direction

Define a common `apply_radio_config(snapshot) -> ApplyResult` interface with explicit supported/unsupported fields.

## What needs to change

Makes partial hardware application impossible to mistake for full success and simplifies ConfigManager.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-005/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/config_manager.py` lines 76–149

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config_manager.py#L76-L149)

```text
   76 |     def _apply_live_radio_config(self) -> bool:
   77 |         radio = getattr(self.daemon, "radio", None)
   78 |         if radio is None:
   79 |             logger.warning("Radio not available for live update")
   80 |             return False
   81 | 
   82 |         radio_cfg = self._get_live_radio_snapshot()
   83 | 
   84 |         try:
   85 |             if hasattr(radio, "configure_radio"):
   86 |                 if hasattr(radio, "radio_config") and isinstance(radio.radio_config, dict):
   87 |                     radio.radio_config.update(radio_cfg)
   88 | 
   89 |                 applied = radio.configure_radio(
   90 |                     frequency=radio_cfg["frequency"],
   91 |                     bandwidth=radio_cfg["bandwidth"],
   92 |                     spreading_factor=radio_cfg["spreading_factor"],
   93 |                     coding_rate=radio_cfg["coding_rate"],
   94 |                 )
   95 |                 if not applied:
   96 |                     logger.warning("Live radio reconfiguration failed")
   97 |                     return False
   98 |             else:
   99 |                 current_frequency = getattr(radio, "frequency", None)
  100 |                 current_bandwidth = getattr(radio, "bandwidth", None)
  101 |                 current_spreading_factor = getattr(radio, "spreading_factor", None)
  102 |                 current_coding_rate = getattr(radio, "coding_rate", None)
  103 |                 current_tx_power = getattr(radio, "tx_power", None)
  104 | 
  105 |                 if (
  106 |                     current_frequency != radio_cfg["frequency"]
  107 |                     and hasattr(radio, "set_frequency")
  108 |                     and not radio.set_frequency(radio_cfg["frequency"])
  109 |                 ):
  110 |                     return False
  111 | 
  112 |                 if (
  113 |                     current_tx_power != radio_cfg["tx_power"]
  114 |                     and hasattr(radio, "set_tx_power")
  115 |                     and not radio.set_tx_power(radio_cfg["tx_power"])
  116 |                 ):
  117 |                     return False
  118 | 
  119 |                 coding_rate_changed = current_coding_rate != radio_cfg["coding_rate"]
  120 |                 if coding_rate_changed:
  121 |                     setattr(radio, "coding_rate", radio_cfg["coding_rate"])
  122 | 
  123 |                 if current_spreading_factor != radio_cfg["spreading_factor"]:
  124 |                     if not hasattr(radio, "set_spreading_factor"):
  125 |                         return False
  126 |                     if not radio.set_spreading_factor(radio_cfg["spreading_factor"]):
  127 |                         return False
  128 | 
  129 |                 if current_bandwidth != radio_cfg["bandwidth"]:
  130 |                     if not hasattr(radio, "set_bandwidth"):
  131 |                         return False
  132 |                     if not radio.set_bandwidth(radio_cfg["bandwidth"]):
  133 |                         return False
  134 |                 elif coding_rate_changed:
  135 |                     if hasattr(radio, "set_bandwidth"):
  136 |                         if not radio.set_bandwidth(radio_cfg["bandwidth"]):
  137 |                             return False
  138 |                     elif hasattr(radio, "set_spreading_factor"):
  139 |                         if not radio.set_spreading_factor(radio_cfg["spreading_factor"]):
  140 |                             return False
  141 |                     else:
  142 |                         return False
  143 | 
  144 |             self._sync_repeater_handler_radio_config(radio_cfg)
  145 |             logger.info("Applied live radio configuration to running daemon")
  146 |             return True
  147 |         except Exception as e:
  148 |             logger.error(f"Failed to apply live radio config: {e}", exc_info=True)
  149 |             return False
```

### Evidence 2: `src/openhop_core/hardware/sx1262_wrapper.py` lines 1622–1684

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/sx1262_wrapper.py#L1622-L1684)

```text
 1622 |     def configure_radio(
 1623 |         self,
 1624 |         frequency: Optional[int] = None,
 1625 |         bandwidth: Optional[int] = None,
 1626 |         spreading_factor: Optional[int] = None,
 1627 |         coding_rate: Optional[int] = None,
 1628 |     ) -> bool:
 1629 |         """Reconfigure LoRa parameters inline without restarting the radio.
 1630 | 
 1631 |         Any omitted parameter retains its current value. Waits for any
 1632 |         in-flight TX to complete before touching the hardware, then restores
 1633 |         RX_CONTINUOUS so the caller does not need to restart.
 1634 |         """
 1635 |         if not self._initialized or self.lora is None:
 1636 |             logger.error("Cannot configure radio: not initialised")
 1637 |             return False
 1638 | 
 1639 |         freq = frequency if frequency is not None else self.frequency
 1640 |         bw = bandwidth if bandwidth is not None else self.bandwidth
 1641 |         sf = spreading_factor if spreading_factor is not None else self.spreading_factor
 1642 |         cr = coding_rate if coding_rate is not None else self.coding_rate
 1643 |         ldro = sf >= 11 and bw <= 125000
 1644 | 
 1645 |         deadline = time.monotonic() + 10.0
 1646 |         while self._tx_lock.locked():
 1647 |             if time.monotonic() > deadline:
 1648 |                 logger.error("configure_radio: TX did not complete within 10s")
 1649 |                 return False
 1650 |             time.sleep(0.05)
 1651 | 
 1652 |         try:
 1653 |             self.lora.clearIrqStatus(0xFFFF)
 1654 |             self.lora.setStandby(self.lora.STANDBY_RC)
 1655 |             time.sleep(self._RADIO_TIMING_DELAY)
 1656 |             self.lora.setFrequency(freq)
 1657 |             self.lora.setLoRaModulation(sf, bw, cr, ldro)
 1658 |             self.frequency = freq
 1659 |             self.bandwidth = bw
 1660 |             self.spreading_factor = sf
 1661 |             self.coding_rate = cr
 1662 |             self._noise_floor = -99.0
 1663 |             self._num_floor_samples = 0
 1664 |             self._floor_sample_sum = 0.0
 1665 |             rx_mask = self._get_rx_irq_mask()
 1666 |             self.lora.clearIrqStatus(0xFFFF)
 1667 |             self.lora.setDioIrqParams(
 1668 |                 rx_mask, rx_mask, self.lora.IRQ_NONE, self.lora.IRQ_NONE
 1669 |             )
 1670 |             self.lora.request(self.lora.RX_CONTINUOUS)
 1671 |             time.sleep(self._RADIO_TIMING_DELAY)
 1672 |             self.lora.clearIrqStatus(0xFFFF)
 1673 |             self._control_tx_rx_pins(tx_mode=False)
 1674 |             logger.info(
 1675 |                 "Radio reconfigured: %.3f MHz BW=%.1f kHz SF%d CR4/%d",
 1676 |                 freq / 1e6,
 1677 |                 bw / 1000,
 1678 |                 sf,
 1679 |                 cr,
 1680 |             )
 1681 |             return True
 1682 |         except Exception as e:
 1683 |             logger.error("Failed to configure radio: %s", e)
 1684 |             return False
```

### Evidence 3: `src/openhop_core/hardware/sx1262_wrapper.py` lines 1589–1598

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/sx1262_wrapper.py#L1589-L1598)

```text
 1589 |     def set_tx_power(self, power: int) -> bool:
 1590 |         """Set TX power in dBm"""
 1591 | 
 1592 |         def set_power():
 1593 |             self.tx_power = power
 1594 |             self.lora.setTxPower(power, self.lora.TX_POWER_SX1262)
 1595 | 
 1596 |         return self._safe_radio_operation(
 1597 |             "set TX power", set_power, f"TX power set to {power} dBm"
 1598 |         )
```
