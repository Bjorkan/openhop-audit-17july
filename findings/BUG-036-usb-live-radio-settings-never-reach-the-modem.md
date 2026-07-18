# BUG-036 — USB live radio setters report success without sending configuration to the modem

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | USB radio live configuration |
| Components | OpenHop Core + OpenHop Repeater |
| Audit date | 2026-07-17 |

## TL;DR

The USB adapter’s live setters only modify Python attributes and return `True`. Repeater `ConfigManager` treats those return values as successful hardware application, so runtime/UI state can claim the radio changed while the modem retains its previous settings.

## Expected behavior

A successful live update must issue the corresponding modem command and confirm acceptance, or explicitly report restart required/unsupported.

## Required direction

1. Implement setters using the modem command protocol, preferably via one atomic `set_config` operation.
2. Expose radio capabilities so Repeater can distinguish live-supported, restart-required, and failed changes.
3. Do not update effective fields until the modem accepts the command.

## Triple verification

| Method | Check | Result | Observation |
|---:|---|---|---|
| 1 | Static setter trace | **Passed** | All ConfigManager-visible setters only assign attributes and return true. |
| 2 | Direct setter | **Passed** | Frequency changes locally with zero serial writes. |
| 3 | ConfigManager integration | **Passed** | Repeater reports live-update success while zero modem writes occur. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition.

## Implementation plan

See [`implementation-plans/BUG-036/implementation_plan.md`](../implementation-plans/BUG-036/implementation_plan.md).

## Source evidence

### Evidence 1: `src/openhop_core/hardware/usb_radio.py` lines 1011–1031

[Open source path](https://github.com/openhop-dev/openhop_core/blob/dev/src/openhop_core/hardware/usb_radio.py#L1011-L1031)

```text
 1011 |     # ── Config setters (for runtime reconfiguration) ──────────
 1012 | 
 1013 |     def set_frequency(self, frequency: int) -> bool:
 1014 |         self.frequency = frequency
 1015 |         return True
 1016 | 
 1017 |     def set_tx_power(self, power: int) -> bool:
 1018 |         self.tx_power = power
 1019 |         return True
 1020 | 
 1021 |     def set_spreading_factor(self, sf: int) -> bool:
 1022 |         self.spreading_factor = sf
 1023 |         return True
 1024 | 
 1025 |     def set_bandwidth(self, bw: int) -> bool:
 1026 |         self.bandwidth = bw
 1027 |         return True
 1028 | 
 1029 |     def __del__(self):
 1030 |         try:
 1031 |             self.cleanup()
```
### Evidence 2: `repeater/config_manager.py` lines 254–369

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/config_manager.py#L254-L369)

```text
  254 |     def live_update_daemon(self, sections: Optional[List[str]] = None) -> bool:
  255 |         """
  256 |         Apply configuration changes to the running daemon's in-memory config.
  257 | 
  258 |         Args:
  259 |             sections: List of config sections to update (e.g., ['repeater', 'delays']).
  260 |                      If None, updates all common sections.
  261 | 
  262 |         Returns:
  263 |             True if live update was successful, False otherwise
  264 |         """
  265 |         if not self.daemon or not hasattr(self.daemon, "config"):
  266 |             logger.warning("Daemon not available for live update")
  267 |             return False
  268 | 
  269 |         try:
  270 |             daemon_config = self.daemon.config
  271 |             live_update_ok = True
  272 | 
  273 |             # Default sections to update if not specified
  274 |             if sections is None:
  275 |                 sections = [
  276 |                     "repeater",
  277 |                     "delays",
  278 |                     "radio",
  279 |                     "acl",
  280 |                     "identities",
  281 |                     "glass",
  282 |                     "http",
  283 |                     "logging",
  284 |                 ]
  285 | 
  286 |             # Update each section
  287 |             for section in sections:
  288 |                 if section in self.config:
  289 |                     if section not in daemon_config:
  290 |                         daemon_config[section] = {}
  291 | 
  292 |                     # Deep copy the section to avoid reference issues
  293 |                     if isinstance(self.config[section], dict):
  294 |                         daemon_config[section].update(self.config[section])
  295 |                     else:
  296 |                         daemon_config[section] = self.config[section]
  297 | 
  298 |                     logger.debug(f"Live updated daemon config section: {section}")
  299 | 
  300 |             logger.info(f"Live updated daemon config sections: {', '.join(sections)}")
  301 | 
  302 |             # Also reload runtime config in RepeaterHandler if delays or repeater sections changed
  303 |             if self.daemon and hasattr(self.daemon, "repeater_handler"):
  304 |                 if any(s in ["delays", "repeater"] for s in sections):
  305 |                     if hasattr(self.daemon.repeater_handler, "reload_runtime_config"):
  306 |                         self.daemon.repeater_handler.reload_runtime_config()
  307 |                         logger.info("Reloaded RepeaterHandler runtime config")
  308 | 
  309 |             # Also reload advert_helper config if repeater section changed
  310 |             if self.daemon and hasattr(self.daemon, "advert_helper") and self.daemon.advert_helper:
  311 |                 if "repeater" in sections:
  312 |                     if hasattr(self.daemon.advert_helper, "reload_config"):
  313 |                         self.daemon.advert_helper.reload_config()
  314 |                         logger.info("Reloaded AdvertHelper config")
  315 | 
  316 |             # Re-apply the flood reception delay base when delays changed
  317 |             if "delays" in sections and self.daemon and getattr(self.daemon, "dispatcher", None):
  318 |                 delays_cfg = self.daemon.config.get("delays", {})
  319 |                 self.daemon.dispatcher.rx_delay_base = float(delays_cfg.get("rx_delay_base", 0.0))
  320 |                 logger.info(
  321 |                     f"Reloaded flood RX delay base: delays.rx_delay_base="
  322 |                     f"{self.daemon.dispatcher.rx_delay_base}"
  323 |                 )
  324 | 
  325 |             # Re-apply dispatcher path hash mode when mesh section changed
  326 |             if "mesh" in sections and self.daemon and hasattr(self.daemon, "dispatcher"):
  327 |                 mesh_cfg = self.daemon.config.get("mesh", {})
  328 |                 path_hash_mode = mesh_cfg.get("path_hash_mode", 0)
  329 |                 if path_hash_mode not in (0, 1, 2):
  330 |                     logger.warning(
  331 |                         f"Invalid mesh.path_hash_mode={path_hash_mode}, must be 0/1/2; using 0"
  332 |                     )
  333 |                     path_hash_mode = 0
  334 |                 self.daemon.dispatcher.set_default_path_hash_mode(path_hash_mode)
  335 |                 logger.info(f"Reloaded path hash mode: mesh.path_hash_mode={path_hash_mode}")
  336 | 
  337 |             if "radio_type" in sections:
  338 |                 logger.info("radio_type change detected; service restart required")
  339 |                 live_update_ok = False
  340 | 
  341 |             if "kiss" in sections and self._kiss_transport_restart_required():
  342 |                 live_update_ok = False
  343 | 
  344 |             if "radio" in sections:
  345 |                 live_update_ok = self._apply_live_radio_config() and live_update_ok
  346 | 
  347 |             if "http" in sections:
  348 |                 live_update_ok = self._apply_live_http_config() and live_update_ok
  349 | 
  350 |             if "logging" in sections:
  351 |                 live_update_ok = self._apply_live_logging_config() and live_update_ok
  352 | 
  353 |             return live_update_ok
  354 | 
  355 |         except Exception as e:
  356 |             logger.error(f"Failed to live update daemon config: {e}", exc_info=True)
  357 |             return False
  358 | 
  359 |     def update_and_save(
  360 |         self,
  361 |         updates: Dict[str, Any],
  362 |         live_update: bool = True,
  363 |         live_update_sections: Optional[List[str]] = None,
  364 |     ) -> Dict[str, Any]:
  365 |         """
  366 |         Apply updates to config, save to file, and optionally live update daemon.
  367 | 
  368 |         This is the main method that should be used by both mesh_cli and api_endpoints.
  369 | 
```

