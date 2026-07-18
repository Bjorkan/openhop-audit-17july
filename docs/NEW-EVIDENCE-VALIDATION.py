from __future__ import annotations
import hashlib, json, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
# Supply source roots when running outside the audit package.
CORE=Path(os.environ["OPENHOP_CORE_ROOT"]).resolve()
REP=Path(os.environ["OPENHOP_REPEATER_ROOT"]).resolve()
roots={"Core":CORE,"Repeater":REP}
items=json.loads((ROOT/"docs/NEW-EVIDENCE-MANIFEST.json").read_text())
errors=[]; total=0
for item in items:
 p=roots[item["repo"]]/item["path"]
 lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
 raw="\n".join(lines[item["start"]-1:item["end"]])+"\n"
 total += item["end"]-item["start"]+1
 got=hashlib.sha256(raw.encode()).hexdigest()
 if got != item["sha256"]: errors.append((item["finding"],str(p),got,item["sha256"]))
print(f"evidence_ranges={len(items)} lines={total} mismatches={len(errors)}")
for e in errors: print(e)
raise SystemExit(bool(errors))
