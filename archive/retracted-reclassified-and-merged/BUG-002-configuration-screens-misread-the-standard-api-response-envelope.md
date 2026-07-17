# RETRACTED — former BUG-002 — configuration screens misread the API response envelope

[← Reverification report](../../docs/REVERIFICATION-REPORT.md) · [← Audit index](../../README.md)

| Field | Value |
|---|---|
| Original classification | Confirmed defect |
| Reverified classification | **Retracted false positive** |
| Audit date | 2026-07-17 |

## Why the earlier claim was wrong

The earlier analysis inspected the Axios interceptor and compiled view code but missed the shared API service wrapper between them. The actual object chain is internally consistent:

1. Axios returns an `AxiosResponse`.
2. The shared API service returns `AxiosResponse.data`.
3. That value is the backend JSON envelope, such as `{success: true, data: {...}}`.
4. Radio and duty-cycle views read the envelope payload through `(await post(...)).data`.
5. The advert view retains the envelope to test `response.success`, then reads `response.data`.

The previous reproduction was a static substring check and did not model this runtime chain. It therefore did not prove the claimed defect.

## Independent verification

`docs/REVERIFICATION-CHECKS.py::test_bug_002_retracted_frontend_correctly_unwraps_axios_then_backend_envelope` verifies the wrapper export, backend envelope and compiled consumer patterns.

## Consequence

No fix should be made for this former finding. Its old implementation plan remains only as an archived warning.
