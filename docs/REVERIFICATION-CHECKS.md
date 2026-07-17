# Independent reverification checks

The earlier audit scripts are archived and are not trusted as proof. This edition uses a replacement pytest suite that checks the supplied snapshots directly, including negative checks for the retracted `BUG-002` and reclassified `BUG-026` claims.

Run from an environment containing the source dependencies:

```bash
OPENHOP_CORE_ROOT=/path/to/openhop_core OPENHOP_REPEATER_ROOT=/path/to/openhop_repeater pytest -q REVERIFICATION-CHECKS.py
```

- Executable suite: [`REVERIFICATION-CHECKS.py`](REVERIFICATION-CHECKS.py)
- Captured result: [`REVERIFICATION-CHECK-OUTPUT.txt`](REVERIFICATION-CHECK-OUTPUT.txt)
- Result for the audited snapshots: **28 passed**
