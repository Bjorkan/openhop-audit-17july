# Focused reproduction checks

The audit includes an executable Python check script that imports the supplied OpenHop code and uses small mocks only where hardware or CherryPy request state is required.

## Run command

```bash
OPENHOP_REPEATER_ROOT=/path/to/openhop_repeater \
OPENHOP_CORE_ROOT=/path/to/openhop_core \
  python /path/to/audit/docs/REPRODUCTION-CHECKS.py
```

## Covered claims

1. Duty-cycle budget usage differs from actual duty-cycle percentage.
2. Live duty-cycle limit remains cached.
3. Airtime radio parameters remain cached after radio config mutation.
4. The `configure_radio` live path omits TX power.
5. Adaptive advert UI/config keys are ignored by runtime parsing.
6. Advert configuration returns success after save failure.
7. Exported sections are rejected by import.
8. Import returns success after persistence failure.
9. A rejected multi-field request leaves earlier mutations in memory.
10. A forward wall-clock correction empties the rolling airtime window.
11. Quick mode/duty endpoints do not call persistence.
12. Compiled UI response handling conflicts with the backend envelope.

All 12 checks passed against the supplied snapshots. The script is intentionally focused and does not replace the full project test suites.

These are the first-pass checks. See `DEEP-REPRODUCTION-CHECKS.md` for the 15 second-pass checks.
