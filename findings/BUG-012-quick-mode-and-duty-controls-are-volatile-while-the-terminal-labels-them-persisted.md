# BUG-012 — Quick mode and duty controls are volatile while the terminal labels them persisted

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Confirmed defect** |
| Severity | **Medium** |
| Confidence | **Confirmed** |
| Area | Runtime controls / persistence / UI |
| Components | OpenHop Repeater + Web UI |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

`set_mode` and `set_duty_cycle` only mutate memory. The terminal client then fabricates `persisted=true` and `live_update=true`, so operators are told the change is saved even though it disappears after restart.

## What happens now

The endpoints never call `ConfigManager`. Because they mutate the same shared config object, a later unrelated save can also persist the change accidentally, making persistence timing nondeterministic.

## Expected behaviour / proposed direction

The control must be explicitly persistent or explicitly session-only. UI text and API fields must match that choice.

## What needs to change

Prefer routing both endpoints through the transactional config helper and returning the standard envelope. If volatility is intentional, rename them and display “until restart” without fabricating persistence.

## Reproduction / verification

Focused check called both endpoints and observed zero `ConfigManager` calls. Static bundle inspection found the terminal forcibly setting `persisted=true` on the returned object.

See [`docs/REPRODUCTION-CHECKS.md`](../docs/REPRODUCTION-CHECKS.md) and the executable check script.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/BUG-012/implementation_plan.md)


## Source references and excerpts

The terminal statement that fabricates `persisted=true` is captured in [`docs/UI-SOURCE-EXCERPTS.md`](../docs/UI-SOURCE-EXCERPTS.md).

### Evidence 1: `repeater/web/api_endpoints.py` lines 1868–1915

[Open source path](https://github.com/openhop-dev/openhop_repeater/blob/dev/repeater/web/api_endpoints.py#L1868-L1915)

```text
 1868 |     @cherrypy.expose
 1869 |     @cherrypy.tools.json_out()
 1870 |     @cherrypy.tools.json_in()
 1871 |     def set_mode(self):
 1872 |         # Enable CORS for this endpoint only if configured
 1873 |         self._set_cors_headers()
 1874 | 
 1875 |         if cherrypy.request.method == "OPTIONS":
 1876 |             return ""
 1877 | 
 1878 |         try:
 1879 |             self._require_post()
 1880 |             data = cherrypy.request.json
 1881 |             new_mode = data.get("mode", "forward")
 1882 |             if new_mode not in ["forward", "monitor", "no_tx"]:
 1883 |                 return self._error("Invalid mode. Must be 'forward', 'monitor', or 'no_tx'")
 1884 |             if "repeater" not in self.config:
 1885 |                 self.config["repeater"] = {}
 1886 |             self.config["repeater"]["mode"] = new_mode
 1887 |             logger.info(f"Mode changed to: {new_mode}")
 1888 |             return {"success": True, "mode": new_mode}
 1889 |         except cherrypy.HTTPError:
 1890 |             # Re-raise HTTP errors (like 405 Method Not Allowed) without logging
 1891 |             raise
 1892 |         except Exception as e:
 1893 |             logger.error(f"Error setting mode: {e}", exc_info=True)
 1894 |             return self._error(e)
 1895 | 
 1896 |     @cherrypy.expose
 1897 |     @cherrypy.tools.json_out()
 1898 |     @cherrypy.tools.json_in()
 1899 |     def set_duty_cycle(self):
 1900 |         # Enable CORS for this endpoint only if configured
 1901 |         self._set_cors_headers()
 1902 | 
 1903 |         if cherrypy.request.method == "OPTIONS":
 1904 |             return ""
 1905 | 
 1906 |         try:
 1907 |             self._require_post()
 1908 |             data = cherrypy.request.json
 1909 |             enabled = data.get("enabled", True)
 1910 |             if "duty_cycle" not in self.config:
 1911 |                 self.config["duty_cycle"] = {}
 1912 |             self.config["duty_cycle"]["enforcement_enabled"] = enabled
 1913 |             logger.info(f"Duty cycle enforcement {'enabled' if enabled else 'disabled'}")
 1914 |             return {"success": True, "enabled": enabled}
 1915 |         except cherrypy.HTTPError:
```
