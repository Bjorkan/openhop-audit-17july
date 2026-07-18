# BUG-045 — Mesh CLI security commands write a configuration section authentication does not read

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. This report was included only after three independent checks passed.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | 🔴 **High** |
| Confidence | **Triple-verified** |
| Area | Authentication configuration |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |

## TL;DR

Mesh CLI writes top-level `security.password` and `security.guest_password`. `LoginHelper` reads `repeater.security.admin_password` and `guest_password`, matching the example configuration. Commands can claim credentials changed while actual authentication continues using the old nested values.

## Expected behavior

Every credential writer and reader must use one canonical schema and field names.

## Required direction

1. Move Mesh CLI writers/getters to `repeater.security.admin_password` and `guest_password`.
2. Provide an explicit migration for any already-written top-level legacy values; do not silently prioritize ambiguous duplicates.
3. Centralize credential access through a typed security configuration helper.

## Triple verification

| Method | Check | Result | Observation |
|---|---|---|---|
| Static runtime trace | CLI writer to authentication reader | **Passed** | CLI and `LoginHelper` use different configuration subtrees and admin-key names. |
| Executable reproduction | Public security commands | **Passed** | Commands report success while the authentication subtree remains unchanged. |
| Active falsification | Actual `LoginHelper` construction | **Passed** | The real helper builds its ACL from the old nested credentials; no alias maps the CLI-written values. |

The executable checks are preserved under [`docs/triple-verification/`](../docs/triple-verification/) and were rerun from clean Python processes for this edition. The third row is an explicit falsification/countercheck that searches for a guard, alternate adapter, normalization, documented contract or unreachable-state explanation that would invalidate the finding.

## Implementation plan

See [`implementation-plans/BUG-045/implementation_plan.md`](../implementation-plans/BUG-045/implementation_plan.md).

## Source evidence

### Evidence 1: `repeater/handler_helpers/mesh_cli.py` lines 446–470

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/mesh_cli.py#L446-L470)

```text
  446 | 
  447 |         if not new_password:
  448 |             return "Error: Password cannot be empty"
  449 | 
  450 |         # Update security config
  451 |         if "security" not in self.config:
  452 |             self.config["security"] = {}
  453 | 
  454 |         self.config["security"]["password"] = new_password
  455 | 
  456 |         # Save config and live update
  457 |         try:
  458 |             saved, err = self.config_manager.save_to_file()
  459 |             if not saved:
  460 |                 logger.error(f"Failed to save password: {err}")
  461 |                 return f"Error: Failed to save config: {err}"
  462 |             self.config_manager.live_update_daemon(["security"])
  463 |             return f"password now: {new_password}"
  464 |         except Exception as e:
  465 |             logger.error(f"Failed to save password: {e}")
  466 |             return "Error: Failed to save password"
  467 | 
  468 |     def _cmd_clear_stats(self) -> str:
  469 |         """Clear statistics."""
  470 |         # TODO: Implement stats clearing
```
### Evidence 2: `repeater/handler_helpers/mesh_cli.py` lines 677–690

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/mesh_cli.py#L677-L690)

```text
  677 |                 return "OK"
  678 | 
  679 |             elif key == "guest.password":
  680 |                 if "security" not in self.config:
  681 |                     self.config["security"] = {}
  682 |                 self.config["security"]["guest_password"] = value
  683 |                 saved, _ = self.config_manager.save_to_file()
  684 |                 self.config_manager.live_update_daemon(["security"])
  685 |                 return "OK"
  686 | 
  687 |             elif key == "owner.info":
  688 |                 self.repeater_config["owner_info"] = value.replace("|", "\n")
  689 |                 saved, _ = self.config_manager.save_to_file()
  690 |                 self.config_manager.live_update_daemon(["repeater"])
```
### Evidence 3: `repeater/handler_helpers/login.py` lines 91–119

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/handler_helpers/login.py#L91-L119)

```text
   91 |             security = config.get("repeater", {}).get("security", {})
   92 |             admin_password = security.get("admin_password") or None
   93 |             guest_password = security.get("guest_password") or None
   94 |             final_security = {
   95 |                 "max_clients": security.get("max_clients", 10),
   96 |                 "admin_password": admin_password,
   97 |                 "guest_password": guest_password,
   98 |                 "allow_read_only": security.get("allow_read_only", False),
   99 |             }
  100 |             if not admin_password and not guest_password:
  101 |                 logger.warning(
  102 |                     f"Repeater '{name}' has no admin/guest password configured; setup is required before login."
  103 |                 )
  104 |             logger.debug(
  105 |                 f"Repeater security config: admin_pw={'SET' if final_security['admin_password'] else 'NONE'}, "
  106 |                 f"guest_pw={'SET' if final_security['guest_password'] else 'NONE'}, "
  107 |                 f"max_clients={final_security['max_clients']}"
  108 |             )
  109 | 
  110 |         # Create ACL for this identity
  111 |         identity_acl = ACL(
  112 |             max_clients=final_security["max_clients"],
  113 |             admin_password=final_security["admin_password"],
  114 |             guest_password=final_security["guest_password"],
  115 |             allow_read_only=final_security["allow_read_only"],
  116 |         )
  117 | 
  118 |         self.acls[hash_byte] = identity_acl
  119 |         logger.info(f"Created ACL for {identity_type} '{name}': hash=0x{hash_byte:02X}")
```
### Evidence 4: `config.yaml.example` lines 114–135

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/config.yaml.example#L114-L135)

```text
  114 |       # Above busy_max = CONGESTED tier (0.25x capacity)
  115 | 
  116 |   # Security settings for login/authentication (shared across all identities)
  117 |   security:
  118 |     # Maximum number of authenticated clients (across all identities)
  119 |     max_clients: 1
  120 | 
  121 |     # Admin password for full access
  122 |     admin_password: "admin123"
  123 | 
  124 |     # Guest password for limited access
  125 |     guest_password: "guest123"
  126 | 
  127 |     # Allow read-only access for clients without password/not in ACL
  128 |     allow_read_only: false
  129 | 
  130 |     # JWT secret key for signing tokens (auto-generated if not provided)
  131 |     # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
  132 |     jwt_secret: ""
  133 | 
  134 |     # JWT token expiry time in minutes (default: 60 minutes / 1 hour)
  135 |     # Controls how long users stay logged in before needing to re-authenticate
```

