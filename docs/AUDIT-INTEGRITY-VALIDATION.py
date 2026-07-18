"""Structural and cross-document validation for the updated audit package."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "findings"
PLANS = ROOT / "implementation-plans"
ARCHIVE = ROOT / "archive" / "retracted-reclassified-and-merged"
DOCS = ROOT / "docs"

bug_files = sorted(FINDINGS.glob("BUG-*.md"))
pe_files = sorted(FINDINGS.glob("POSSIBLE-ENHANCEMENT-*.md"))
expected_bugs = {f"BUG-{n:03d}" for n in ([1] + list(range(3, 26)) + list(range(27, 50)))}
expected_pes = {f"POSSIBLE-ENHANCEMENT-{n:03d}" for n in range(1, 19)}

def fid(path: Path) -> str:
    m = re.match(r"^(BUG-\d{3}|POSSIBLE-ENHANCEMENT-\d{3})-", path.name)
    assert m, path
    return m.group(1)

active_bug_ids = {fid(p) for p in bug_files}
active_pe_ids = {fid(p) for p in pe_files}
assert len(bug_files) == len(active_bug_ids) == 47
assert len(pe_files) == len(active_pe_ids) == 18
assert active_bug_ids == expected_bugs, active_bug_ids ^ expected_bugs
assert active_pe_ids == expected_pes, active_pe_ids ^ expected_pes

# Every active bug must explicitly preserve all three admission methods.
for path in bug_files:
    text = path.read_text(encoding="utf-8", errors="replace")
    assert "## Triple verification" in text, path.name
    assert "Static" in text and "Executable" in text and "falsification" in text.lower(), path.name
    assert "Triple-verified" in text, path.name
    plan_id = fid(path)
    assert f"../implementation-plans/{plan_id}/implementation_plan.md" in text, path.name

# Active enhancements remain enhancements, not defect claims.
for path in pe_files:
    text = path.read_text(encoding="utf-8", errors="replace")
    assert "Possible enhancement" in text or "possible enhancement" in text, path.name
    assert f"../implementation-plans/{fid(path)}/implementation_plan.md" in text, path.name

plan_files = sorted(PLANS.glob("*/implementation_plan.md"))
plan_ids = {p.parent.name for p in plan_files}
assert len(plan_files) == len(plan_ids) == 65
assert plan_ids == active_bug_ids | active_pe_ids
required_plan_headings = (
    "## Objective",
    "## Required outcome",
    "## Repositories and files to inspect or change",
    "## Implementation work packages",
    "## Decisions and assumptions to double-check",
    "## Test plan",
    "## Compatibility, rollout and rollback",
    "## Definition of done",
)
for plan in plan_files:
    text = plan.read_text(encoding="utf-8", errors="replace")
    for heading in required_plan_headings:
        assert heading in text, (plan.parent.name, heading)
    finding = next(p for p in bug_files + pe_files if fid(p) == plan.parent.name)
    assert f"../../findings/{finding.name}" in text, plan.parent.name


# Severity and evidence-line consistency between findings, index and plans.
readme = (ROOT / "README.md").read_text(encoding="utf-8")
evidence_plan_rows = 0
for finding in bug_files + pe_files:
    finding_id = fid(finding)
    finding_text = finding.read_text(encoding="utf-8", errors="replace")
    severity = re.search(r"\| Severity \| (?:[🔴🟠🟡] )?\*\*(High|Medium|Low|Enhancement)\*\* \|", finding_text)
    assert severity, finding.name
    plan_text = (PLANS / finding_id / "implementation_plan.md").read_text(encoding="utf-8", errors="replace")
    plan_severity = re.search(r"\| Severity \| (?:[🔴🟠🟡] )?\*\*(High|Medium|Low|Enhancement)\*\* \|", plan_text)
    assert plan_severity and plan_severity.group(1) == severity.group(1), finding_id
    if finding_id.startswith("BUG-"):
        index_severity = re.search(rf"\| [^\n]*\[{finding_id}\]\([^\n]+?\) \| (High|Medium|Low) \|", readme)
        assert index_severity and index_severity.group(1) == severity.group(1), finding_id
    for line in plan_text.splitlines():
        match = re.match(r"^\|\s*OpenHop[^|]*\|\s*`([^`]+)`\s*\|\s*Evidence lines\s+(\d+)[–-](\d+)\s*\|", line)
        if not match:
            continue
        evidence_plan_rows += 1
        source_path, start_line, end_line = match.groups()
        heading = rf"### Evidence \d+: `{re.escape(source_path)}` lines {start_line}[–-]{end_line}"
        assert re.search(heading, finding_text), (finding_id, source_path, start_line, end_line)

# Archived/reclassified IDs must not also be active.
archive_names = {p.name for p in ARCHIVE.glob("*.md")}
for prefix in ("BUG-002-", "BUG-026-", "POSSIBLE-ENHANCEMENT-019-", "POSSIBLE-ENHANCEMENT-020-"):
    assert any(name.startswith(prefix) for name in archive_names), prefix
assert "BUG-002" not in active_bug_ids and "BUG-026" not in active_bug_ids

# Key executable and factual result records.
assert "28 passed" in (DOCS / "REVERIFICATION-CHECK-OUTPUT.txt").read_text()
assert "falsification_passed=25 failed=0" in (DOCS / "BASELINE-FALSIFICATION-CHECK-OUTPUT.txt").read_text()
assert "20 enhancement premises verified" in (DOCS / "ENHANCEMENT-PREMISE-CHECK-OUTPUT.txt").read_text()
assert "1331 passed" in (DOCS / "CORE-FULL-RERUN-OUTPUT.txt").read_text()
repeater_output = (DOCS / "REPEATER-FULL-RERUN-OUTPUT.txt").read_text()
assert "1 failed, 1221 passed, 7 warnings" in repeater_output
assert "test_bridge_accepts_host_radio_callbacks" in repeater_output
assert "BUG-049: 3/3 checks passed" in (DOCS / "triple-verification/verify_bug_049.out").read_text()
assert "checked excerpt lines 5901\nerrors 0" in (DOCS / "EVIDENCE-EXCERPT-VALIDATION-OUTPUT.txt").read_text()
assert "evidence_ranges=60 lines=1530 mismatches=0" in (DOCS / "NEW-EVIDENCE-VALIDATION-OUTPUT.txt").read_text()
assert "missing_existing_paths=0" in (DOCS / "PLAN-PATH-VALIDATION-OUTPUT.txt").read_text()
assert "Core extracted-tree differences from a fresh extraction: 0" in (DOCS / "SOURCE-IMMUTABILITY-VALIDATION-OUTPUT.txt").read_text()
assert "Repeater extracted-tree differences from a fresh extraction: 0" in (DOCS / "SOURCE-IMMUTABILITY-VALIDATION-OUTPUT.txt").read_text()

# Summary/index consistency.
for fragment in (
    "Confirmed active defects after update | **47**",
    "Active possible enhancements | **18**",
    "Active implementation plans | **65**",
    "Baseline active-falsification checks | **25/25 passed**",
    "Core tests | **1,331 passed**",
    "Repeater tests | **1,221 passed, 1 failed, 7 warnings**",
):
    assert fragment in readme, fragment

# No patch payloads or duplicated result formats.
patches = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in {".patch", ".diff"}]
assert not patches, patches

print("active_bugs=47")
print("active_enhancements=18")
print("active_plans=65")
print("active_bug_triple_verification=47/47")
print("baseline_falsification=25/25")
print("severity_consistency=65/65")
print(f"plan_evidence_line_rows={evidence_plan_rows}/76")
print("archived_classifications=4")
print("patch_files=0")
print("result=PASS")
