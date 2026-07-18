# BUG-046 — Mesh CLI documents frequency in MHz but stores the value as Hz

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | Mesh CLI / radio units |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## TL;DR

The CLI help says `set freq <mhz>` and the getter converts stored Hz to MHz, but the setter stores the raw decimal token in the Hz field. `869.618` is persisted as `869.618` and live application truncates it to `869` Hz.

## Expected behavior

The setter must convert MHz to integer Hz with validation before persistence and hardware application.

## Required direction

1. Parse with `Decimal` or a clearly documented numeric conversion and multiply by 1,000,000.
2. Validate the resulting frequency against the supported regional/radio range before mutating configuration.
3. Use a shared frequency parser/formatter for CLI, API and configuration.

## Triple verification

| Method | Check | Result | Observation |
|---:|---|---|---|
| 1 | Static help/getter/setter trace | **Passed** | Help/get use MHz, setter writes raw value. |
| 2 | Public command persistence | **Passed** | `869.618` is stored unchanged in the frequency field. |
| 3 | Live application | **Passed** | ConfigManager converts the stored value to integer 869 and applies it as Hz. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition.

## Implementation plan

See [`implementation-plans/BUG-046/implementation_plan.md`](../implementation-plans/BUG-046/implementation_plan.md).

## Source evidence

### Evidence 1: `repeater/handler_helpers/mesh_cli.py` lines 320–330

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/mesh_cli.py#L320-L330)

```text
  320 |             "set": (
  321 |                 "Set commands \u2014 set <param> <value>:\n"
  322 |                 "  set name <name>        Set node name\n"
  323 |                 "  set radio <f> <bw> <sf> <cr>  Set radio (restart required)\n"
  324 |                 "  set freq <mhz>         Set frequency (restart required)\n"
  325 |                 "  set tx <power>         Set TX power\n"
  326 |                 "  set af <factor>        Airtime factor\n"
  327 |                 "  set repeat on|off      Enable/disable repeating\n"
  328 |                 "  set lat <deg>          Latitude\n"
  329 |                 "  set lon <deg>          Longitude\n"
  330 |                 "  set guest.password <pw> Guest password\n"
```
### Evidence 2: `repeater/handler_helpers/mesh_cli.py` lines 507–519

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/mesh_cli.py#L507-L519)

```text
  507 |             freq_hz = radio.get("frequency", 915000000)
  508 |             bw_hz = radio.get("bandwidth", 125000)
  509 |             sf = radio.get("spreading_factor", 7)
  510 |             cr = radio.get("coding_rate", 5)
  511 |             # Convert Hz to MHz for freq, Hz to kHz for bandwidth (match C++ ftoa output)
  512 |             freq_mhz = freq_hz / 1_000_000.0
  513 |             bw_khz = bw_hz / 1_000.0
  514 |             return f"> {freq_mhz},{bw_khz},{sf},{cr}"
  515 | 
  516 |         elif param == "freq":
  517 |             freq_hz = self.config.get("radio", {}).get("frequency", 915000000)
  518 |             freq_mhz = freq_hz / 1_000_000.0
  519 |             return f"> {freq_mhz}"
```
### Evidence 3: `repeater/handler_helpers/mesh_cli.py` lines 661–674

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/mesh_cli.py#L661-L674)

```text
  661 |                 return "OK - restart repeater to apply"
  662 | 
  663 |             elif key == "freq":
  664 |                 if "radio" not in self.config:
  665 |                     self.config["radio"] = {}
  666 |                 self.config["radio"]["frequency"] = float(value)
  667 |                 saved, _ = self.config_manager.save_to_file()
  668 |                 self.config_manager.live_update_daemon(["radio"])
  669 |                 return "OK - restart repeater to apply"
  670 | 
  671 |             elif key == "tx":
  672 |                 if "radio" not in self.config:
  673 |                     self.config["radio"] = {}
  674 |                 self.config["radio"]["tx_power"] = int(value)
```
### Evidence 4: `repeater/config_manager.py` lines 27–41

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config_manager.py#L27-L41)

```text
   27 | 
   28 |     def _get_live_radio_snapshot(self) -> Dict[str, Any]:
   29 |         radio_cfg = self.config.get("radio", {}) or {}
   30 |         return {
   31 |             "frequency": int(radio_cfg.get("frequency", 0) or 0),
   32 |             "bandwidth": int(radio_cfg.get("bandwidth", 0) or 0),
   33 |             "spreading_factor": int(radio_cfg.get("spreading_factor", 0) or 0),
   34 |             "coding_rate": int(radio_cfg.get("coding_rate", 0) or 0),
   35 |             "tx_power": int(radio_cfg.get("tx_power", 0) or 0),
   36 |         }
   37 | 
   38 |     def _sync_repeater_handler_radio_config(self, radio_cfg: Dict[str, Any]) -> None:
   39 |         repeater_handler = getattr(self.daemon, "repeater_handler", None)
   40 |         if not repeater_handler or not hasattr(repeater_handler, "radio_config"):
   41 |             return
```

