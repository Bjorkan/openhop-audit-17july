# BUG-008 — Configuration export cannot be fully restored by configuration import

[← Audit index](../README.md)

> Triple-verification verdict: **confirmed against the supplied snapshots**. The finding survived an independent static runtime trace, executable reproduction and active falsification pass on 18 July 2026.

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **High** |
| Confidence | **Triple-verified** |
| Area | Backup and restore |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |
| Independent recheck | 2026-07-18 |
| Status | Open in supplied snapshot |

## TL;DR

`config_export` advertises a full configuration backup, but `config_import` silently skips several sections that are present in the shipped configuration and export.

## What happens now

The import allowlist omits at least `duty_cycle`, `gps`, `http`, `policy`, `sensors`, and `storage`. A backup can therefore report successful import while leaving these settings unchanged; importing a backup containing only one omitted section fails as “no valid sections.”

## Expected behaviour / proposed direction

Every supported exported section must have an explicit restore policy. Unsupported sections should be listed as errors, not silently skipped.

## What needs to change

Derive importability from a shared schema, return `sections_skipped` with reasons, and add an export→import round-trip test covering every top-level section.

## Reproduction / verification

Focused check attempted to restore the exported `duty_cycle` section and received “No valid configuration sections found,” with the current value unchanged.

See [`docs/REVERIFICATION-CHECKS.md`](../docs/REVERIFICATION-CHECKS.md) and the executable check script.

## Triple verification

| Method | Result | Record |
|---|---|---|
| Static runtime trace | **Passed** | The complete reachable path and exact quoted source excerpts in this report were revalidated byte-for-byte against the supplied source trees. |
| Executable reproduction | **Passed** | `test_bug_008_confirmed_exported_top_level_sections_are_skipped_by_import` in [`REVERIFICATION-CHECKS.py`](../docs/REVERIFICATION-CHECKS.py). |
| Active falsification | **Passed** | No alternate full-restore mode exists for sections included by export but excluded by import. See [`BASELINE-FALSIFICATION-CHECKS.py`](../docs/BASELINE-FALSIFICATION-CHECKS.py). |

The consolidated baseline matrix and captured results are in [`BASELINE-TRIPLE-VERIFICATION.md`](../docs/BASELINE-TRIPLE-VERIFICATION.md).

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-008/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/web/api_endpoints.py` lines 7166–7240

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L7166-L7240)

```text
 7166 |     @cherrypy.expose
 7167 |     @cherrypy.tools.json_out()
 7168 |     def config_export(self, include_secrets=None):
 7169 |         """Export the full configuration as JSON.
 7170 | 
 7171 |         GET /api/config_export
 7172 |         GET /api/config_export?include_secrets=true   (full backup with secrets)
 7173 | 
 7174 |         By default, sensitive fields (passwords, JWT secrets, identity keys)
 7175 |         are redacted.  Pass ?include_secrets=true for a full backup that
 7176 |         includes all secrets — required for restoring to a new device.
 7177 | 
 7178 |         Returns: {"success": true, "data": {"meta": {...}, "config": {...}}}
 7179 |         """
 7180 |         self._set_cors_headers()
 7181 |         if cherrypy.request.method == "OPTIONS":
 7182 |             return ""
 7183 |         try:
 7184 |             import copy
 7185 | 
 7186 |             full_backup = str(include_secrets).lower() in ("true", "1", "yes")
 7187 |             exported = copy.deepcopy(self.config)
 7188 | 
 7189 |             if full_backup:
 7190 |                 # Convert binary identity key to hex for JSON serialisation
 7191 |                 rep = exported.get("repeater", {})
 7192 |                 if "identity_key" in rep and isinstance(rep["identity_key"], bytes):
 7193 |                     rep["identity_key"] = rep["identity_key"].hex()
 7194 | 
 7195 |                 # Convert identity keys in companion / room_server configs
 7196 |                 for section in ("room_servers", "companions"):
 7197 |                     entries = exported.get("identities", {}).get(section, []) or []
 7198 |                     for entry in entries:
 7199 |                         if isinstance(entry.get("identity_key"), bytes):
 7200 |                             entry["identity_key"] = entry["identity_key"].hex()
 7201 |             else:
 7202 |                 # Redact sensitive fields
 7203 |                 sec = exported.get("repeater", {}).get("security", {})
 7204 |                 for field in ("admin_password", "guest_password", "jwt_secret"):
 7205 |                     if field in sec:
 7206 |                         sec[field] = "*** REDACTED ***"
 7207 | 
 7208 |                 # Redact repeater identity key
 7209 |                 rep = exported.get("repeater", {})
 7210 |                 if "identity_key" in rep:
 7211 |                     del rep["identity_key"]
 7212 | 
 7213 |                 # Redact identity keys in companion / room_server configs
 7214 |                 for section in ("room_servers", "companions"):
 7215 |                     entries = exported.get("identities", {}).get(section, []) or []
 7216 |                     for entry in entries:
 7217 |                         if "identity_key" in entry:
 7218 |                             entry["identity_key"] = "*** REDACTED ***"
 7219 | 
 7220 |             # Ensure all bytes values are converted to hex for JSON serialisation
 7221 |             def _sanitize(obj):
 7222 |                 if isinstance(obj, bytes):
 7223 |                     return obj.hex()
 7224 |                 if isinstance(obj, dict):
 7225 |                     return {k: _sanitize(v) for k, v in obj.items()}
 7226 |                 if isinstance(obj, list):
 7227 |                     return [_sanitize(v) for v in obj]
 7228 |                 return obj
 7229 | 
 7230 |             exported = _sanitize(exported)
 7231 | 
 7232 |             meta = {
 7233 |                 "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
 7234 |                 "version": __version__,
 7235 |                 "config_path": self._config_path,
 7236 |                 "includes_secrets": full_backup,
 7237 |             }
 7238 | 
 7239 |             return {"success": True, "data": {"meta": meta, "config": exported}}
 7240 | 
```

### Evidence 2: `repeater/web/api_endpoints.py` lines 7297–7329

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L7297-L7329)

```text
 7297 |             data = cherrypy.request.json
 7298 |             imported_config = data.get("config")
 7299 | 
 7300 |             if not imported_config or not isinstance(imported_config, dict):
 7301 |                 return self._error("Missing or invalid 'config' object in request body")
 7302 | 
 7303 |             # Sections we allow to be imported
 7304 |             ALLOWED_SECTIONS = {
 7305 |                 "repeater",
 7306 |                 "mesh",
 7307 |                 "radio",
 7308 |                 "sx1262",
 7309 |                 "ch341",
 7310 |                 "kiss",
 7311 |                 "pymc_usb",
 7312 |                 "pymc_tcp",
 7313 |                 "mqtt_brokers",
 7314 |                 "mqtt",
 7315 |                 "identities",
 7316 |                 "delays",
 7317 |                 "web",
 7318 |                 "letsmesh",
 7319 |                 "glass",
 7320 |                 "logging",
 7321 |                 "radio_type",
 7322 |             }
 7323 | 
 7324 |             updated_sections = []
 7325 |             restart_required = False
 7326 | 
 7327 |             for section, value in imported_config.items():
 7328 |                 if section not in ALLOWED_SECTIONS:
 7329 |                     logger.info(f"Config import: skipping unknown section '{section}'")
```
