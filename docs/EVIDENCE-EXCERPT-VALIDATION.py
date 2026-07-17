from __future__ import annotations

import os
import re
from pathlib import Path

AUDIT_ROOT = Path(os.environ.get('OPENHOP_AUDIT_ROOT', Path(__file__).resolve().parents[1])).resolve()
CORE_ROOT = Path(os.environ['OPENHOP_CORE_ROOT']).resolve()
REPEATER_ROOT = Path(os.environ['OPENHOP_REPEATER_ROOT']).resolve()

errors: list[tuple] = []
checked = 0
pattern = re.compile(
    r'### Evidence \d+: `([^`]+)` lines ([^\n]+)\n.*?```text\n(.*?)\n```',
    re.S,
)

for report in sorted((AUDIT_ROOT / 'findings').glob('*.md')):
    text = report.read_text()
    for source_path, _ranges, block in pattern.findall(text):
        candidates = [CORE_ROOT / source_path, REPEATER_ROOT / source_path]
        existing = [path for path in candidates if path.exists()]
        if len(existing) != 1:
            errors.append((report.name, source_path, 'source resolution', [str(path) for path in existing]))
            continue

        source_lines = existing[0].read_text(errors='replace').splitlines()
        for quoted_line in block.splitlines():
            match = re.match(r'\s*(\d+) \| ?(.*)$', quoted_line)
            if not match:
                if quoted_line.strip():
                    errors.append((report.name, source_path, 'unparsed', quoted_line))
                continue

            line_number = int(match.group(1))
            quoted_content = match.group(2)
            checked += 1
            if line_number < 1 or line_number > len(source_lines):
                errors.append((report.name, source_path, line_number, 'out of range'))
                continue
            if source_lines[line_number - 1] != quoted_content:
                errors.append(
                    (
                        report.name,
                        source_path,
                        line_number,
                        {'expected': source_lines[line_number - 1], 'audit': quoted_content},
                    )
                )

print(f'checked excerpt lines {checked}')
print(f'errors {len(errors)}')
for error in errors[:100]:
    print(error)

if errors:
    raise SystemExit(1)
