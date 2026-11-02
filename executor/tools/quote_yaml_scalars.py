"""Quote single-line plain YAML values that contain ': ' or ' #' (which YAML would misread). Used on problem sources.
Lines inside block scalars (after `key: |` or `key: >`) are code or prose and are never touched."""
import json, re, sys
from pathlib import Path

LINE = re.compile(r"^(\s*(?:- )?)([A-Za-z_]+): (?![\"'|>\[{&*!])(.+)$")
BLOCK = re.compile(r"^(\s*)(?:- )?[A-Za-z_]+: [|>][-+]?\s*$|^(\s*)- [|>][-+]?\s*$")
for path in sys.argv[1:]:
    p = Path(path)
    out, changed, block_indent = [], 0, None
    for line in p.read_text().splitlines():
        indent = len(line) - len(line.lstrip())
        if block_indent is not None:
            if line.strip() == "" or indent > block_indent:
                out.append(line)
                continue
            block_indent = None
        if BLOCK.match(line):
            block_indent = indent
            out.append(line)
            continue
        m = LINE.match(line)
        if m and (": " in m.group(3) or " #" in m.group(3)):
            line = f"{m.group(1)}{m.group(2)}: {json.dumps(m.group(3), ensure_ascii=False)}"
            changed += 1
        out.append(line)
    p.write_text("\n".join(out) + "\n")
    print(f"{path}: quoted {changed}")
