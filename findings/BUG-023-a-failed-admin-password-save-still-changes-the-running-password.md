# BUG-023 — A failed admin-password save still changes the running password

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Confirmed** |
| Area | Authentication / configuration transactions |
| Components | OpenHop Repeater Web API |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

The password is written to the shared in-memory configuration before persistence. If saving fails, the API returns an error but leaves the new password active until restart.

## What happens now

After a disk failure, the old credential no longer matches runtime login checks even though the change response says failure. Restart restores the old persisted password, creating a second reversal. This can lock out an operator or make incident recovery unpredictable.

## Expected behaviour / proposed direction

A failed password-change transaction must leave the active and persisted credential unchanged.

## What needs to change

Validate and stage the new password, persist a copied configuration atomically, then swap the runtime reference. At minimum restore the previous value in every failure path.

## Reproduction / verification

The deeper focused check forced `save_to_file()` to return false. The endpoint returned HTTP 500 while `config[repeater][security][admin_password]` already held the new password.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-023/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/web/auth_endpoints.py` lines 537–605

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/auth_endpoints.py#L537-L605)

```text
  537 |         try:
  538 |             # Parse JSON body manually
  539 |             body = cherrypy.request.body.read().decode("utf-8")
  540 |             data = json.loads(body) if body else {}
  541 | 
  542 |             current_password = data.get("current_password", "")
  543 |             new_password = data.get("new_password", "")
  544 | 
  545 |             if not current_password or not new_password:
  546 |                 cherrypy.response.status = 400
  547 |                 return json.dumps(
  548 |                     {
  549 |                         "success": False,
  550 |                         "error": "Both current_password and new_password are required",
  551 |                     }
  552 |                 ).encode("utf-8")
  553 | 
  554 |             # Validate new password strength
  555 |             if len(new_password) < 8:
  556 |                 cherrypy.response.status = 400
  557 |                 return json.dumps(
  558 |                     {"success": False, "error": "New password must be at least 8 characters long"}
  559 |                 ).encode("utf-8")
  560 | 
  561 |             # Verify current password
  562 |             repeater_config = self.config.get("repeater", {})
  563 |             security_config = repeater_config.get("security", {})
  564 |             config_password = security_config.get("admin_password", "")
  565 | 
  566 |             if not config_password:
  567 |                 cherrypy.response.status = 500
  568 |                 return json.dumps({"success": False, "error": "System configuration error"}).encode(
  569 |                     "utf-8"
  570 |                 )
  571 | 
  572 |             if current_password != config_password:
  573 |                 cherrypy.response.status = 401
  574 |                 return json.dumps(
  575 |                     {"success": False, "error": "Current password is incorrect"}
  576 |                 ).encode("utf-8")
  577 | 
  578 |             # Update password in config
  579 |             if "repeater" not in self.config:
  580 |                 self.config["repeater"] = {}
  581 |             if "security" not in self.config["repeater"]:
  582 |                 self.config["repeater"]["security"] = {}
  583 | 
  584 |             self.config["repeater"]["security"]["admin_password"] = new_password
  585 | 
  586 |             # Save to config file using ConfigManager
  587 |             if self.config_manager:
  588 |                 if self.config_manager.save_to_file():
  589 |                     logger.info(f"Admin password changed successfully by user {user['username']}")
  590 |                     return json.dumps(
  591 |                         {
  592 |                             "success": True,
  593 |                             "message": "Password changed successfully. Please log in again with your new password.",
  594 |                         }
  595 |                     ).encode("utf-8")
  596 |                 else:
  597 |                     cherrypy.response.status = 500
  598 |                     return json.dumps(
  599 |                         {"success": False, "error": "Failed to save password to config file"}
  600 |                     ).encode("utf-8")
  601 |             else:
  602 |                 cherrypy.response.status = 500
  603 |                 return json.dumps(
  604 |                     {"success": False, "error": "Config manager not available"}
  605 |                 ).encode("utf-8")
```
