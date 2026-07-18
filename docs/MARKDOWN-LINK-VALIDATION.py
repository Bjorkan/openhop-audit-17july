"""Validate local relative Markdown links in the audit package."""
from __future__ import annotations
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
markdown_files = sorted(ROOT.rglob("*.md"))
link_re = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)|!\[[^\]]*\]\(([^)]+)\)")
broken: list[tuple[str, str]] = []
count = 0
for path in markdown_files:
    text = path.read_text(encoding="utf-8", errors="replace")
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in link_re.finditer(line):
            target = (match.group(1) or match.group(2) or "").strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            target = target.split("#", 1)[0].strip()
            if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            count += 1
            resolved = (path.parent / unquote(target)).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                broken.append((str(path.relative_to(ROOT)), target))
                continue
            if not resolved.exists():
                broken.append((str(path.relative_to(ROOT)), target))

print(f"markdown_files={len(markdown_files)} relative_links={count} broken={len(broken)}")
for source, target in broken:
    print(f"BROKEN {source}: {target}")
raise SystemExit(bool(broken))
