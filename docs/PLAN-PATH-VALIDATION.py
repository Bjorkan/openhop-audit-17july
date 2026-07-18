"""Validate active finding/plan pairs and concrete source/test paths."""
from __future__ import annotations
import os
import re
from pathlib import Path

AUDIT = Path(__file__).resolve().parents[1]
CORE = Path(os.environ["OPENHOP_CORE_ROOT"]).resolve()
REPEATER = Path(os.environ["OPENHOP_REPEATER_ROOT"]).resolve()

findings = sorted((AUDIT / "findings").glob("*.md"))
plans = sorted((AUDIT / "implementation-plans").glob("*/implementation_plan.md"))
assert len(findings) == 65, len(findings)
assert len(plans) == 65, len(plans)

finding_by_id = {re.match(r"^(BUG-\d{3}|POSSIBLE-ENHANCEMENT-\d{3})-", p.name).group(1): p for p in findings}
plan_by_id = {p.parent.name: p for p in plans}
assert set(finding_by_id) == set(plan_by_id), (set(finding_by_id) ^ set(plan_by_id))

for finding_id, finding in finding_by_id.items():
    expected = f"../implementation-plans/{finding_id}/implementation_plan.md"
    assert expected in finding.read_text(encoding="utf-8"), (finding_id, expected)
    plan = plan_by_id[finding_id]
    expected_back = f"../../findings/{finding.name}"
    assert expected_back in plan.read_text(encoding="utf-8"), (finding_id, expected_back)

repo_roots = {
    "OpenHop Core": CORE,
    "OpenHop Repeater": REPEATER,
    "OpenHop Repeater Web API": REPEATER,
    "OpenHop Repeater Web UI": REPEATER,
    "OpenHop Core + OpenHop Repeater": None,
}
path_refs: list[tuple[str, str, str]] = []
missing: list[tuple[str, str, str]] = []
skipped = 0

for plan in plans:
    text = plan.read_text(encoding="utf-8", errors="replace")
    finding_id = plan.parent.name
    # Repository/path table rows are the authoritative change-surface inventory.
    for line in text.splitlines():
        m = re.match(r"^\|\s*(OpenHop[^|]+?)\s*\|\s*`([^`]+)`\s*\|", line)
        if not m:
            continue
        repo, raw = m.group(1).strip(), m.group(2).strip()
        path_refs.append((finding_id, repo, raw))
        low = raw.lower()
        if "(new)" in low or "not supplied" in low or "corresponding to" in low:
            skipped += 1
            continue
        if any(ch in raw for ch in "*?[]"):
            skipped += 1
            continue
        root = repo_roots.get(repo)
        if root is None:
            # Multi-repository conceptual rows are not concrete paths.
            skipped += 1
            continue
        clean = raw.split(" (", 1)[0].strip().rstrip("/")
        if not (root / clean).exists():
            missing.append((finding_id, repo, clean))

assert not missing, missing
print(f"active_findings={len(findings)}")
print(f"active_plans={len(plans)}")
print(f"finding_plan_pairs={len(plan_by_id)}")
print(f"repository_path_rows={len(path_refs)}")
print(f"skipped_proposed_or_unsupplied={skipped}")
print("missing_existing_paths=0")
print("result=PASS")
