# POSSIBLE-ENHANCEMENT-007 — Possible enhancement — split `APIEndpoints` into domain controllers

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Maintainability |
| Components | OpenHop Repeater |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

`api_endpoints.py` combines configuration, telemetry, packets, storage, identity, backup, discovery, updates and service control in one class.

## What happens now

The supplied file is more than 7,400 lines and contains a large number of exposed methods with repeated request/CORS/error scaffolding.

## Expected behaviour / proposed direction

Create small controllers such as `ConfigAPI`, `RadioAPI`, `TelemetryAPI`, `BackupAPI`, `IdentityAPI` and mount them under the existing route tree.

## What needs to change

Reduces merge conflicts, makes ownership and tests clearer, and exposes duplicated helper opportunities.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-007/implementation_plan.md)


## Source references and excerpts

### Evidence 1: `repeater/web/api_endpoints.py` lines 268–275

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L268-L275)

```text
  268 |     def _success(self, data, **kwargs):
  269 |         result = {"success": True, "data": data}
  270 |         result.update(kwargs)
  271 |         return result
  272 | 
  273 |     def _error(self, error):
  274 |         return {"success": False, "error": str(error)}
  275 | 
```

### Evidence 2: `repeater/web/api_endpoints.py` lines 3962–4020

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L3962-L4020)

```text
 3962 |         try:
 3963 |             self._require_post()
 3964 |             data = cherrypy.request.json or {}
 3965 | 
 3966 |             applied = []
 3967 | 
 3968 |             # Ensure config sections exist
 3969 |             if "radio" not in self.config:
 3970 |                 self.config["radio"] = {}
 3971 |             if "delays" not in self.config:
 3972 |                 self.config["delays"] = {}
 3973 |             if "repeater" not in self.config:
 3974 |                 self.config["repeater"] = {}
 3975 |             if "mesh" not in self.config:
 3976 |                 self.config["mesh"] = {}
 3977 | 
 3978 |             # Update TX power (up to 30 dBm for high-power radios)
 3979 |             if "tx_power" in data:
 3980 |                 power = int(data["tx_power"])
 3981 |                 if power < 2 or power > 30:
 3982 |                     return self._error("TX power must be 2-30 dBm")
 3983 |                 self.config["radio"]["tx_power"] = power
 3984 |                 applied.append(f"power={power}dBm")
 3985 | 
 3986 |             # Update frequency (in Hz)
 3987 |             if "frequency" in data:
 3988 |                 freq = float(data["frequency"])
 3989 |                 if freq < 100_000_000 or freq > 1_000_000_000:
 3990 |                     return self._error("Frequency must be 100-1000 MHz")
 3991 |                 self.config["radio"]["frequency"] = freq
 3992 |                 applied.append(f"freq={freq / 1_000_000:.3f}MHz")
 3993 | 
 3994 |             # Update bandwidth (in Hz)
 3995 |             if "bandwidth" in data:
 3996 |                 bw = int(float(data["bandwidth"]))
 3997 |                 valid_bw = [7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000, 500000]
 3998 |                 if bw not in valid_bw:
 3999 |                     return self._error(
 4000 |                         f"Bandwidth must be one of {[b / 1000 for b in valid_bw]} kHz"
 4001 |                     )
 4002 |                 self.config["radio"]["bandwidth"] = bw
 4003 |                 applied.append(f"bw={bw / 1000}kHz")
 4004 | 
 4005 |             # Update spreading factor
 4006 |             if "spreading_factor" in data:
 4007 |                 sf = int(data["spreading_factor"])
 4008 |                 if sf < 5 or sf > 12:
 4009 |                     return self._error("Spreading factor must be 5-12")
 4010 |                 self.config["radio"]["spreading_factor"] = sf
 4011 |                 applied.append(f"sf={sf}")
 4012 | 
 4013 |             # Update coding rate
 4014 |             if "coding_rate" in data:
 4015 |                 cr = int(data["coding_rate"])
 4016 |                 if cr < 5 or cr > 8:
 4017 |                     return self._error("Coding rate must be 5-8 (for 4/5 to 4/8)")
 4018 |                 self.config["radio"]["coding_rate"] = cr
 4019 |                 applied.append(f"cr=4/{cr}")
 4020 | 
```

### Evidence 3: `repeater/web/api_endpoints.py` lines 7166–7240

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
