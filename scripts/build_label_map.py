#!/usr/bin/env python3
"""Build a unified Obsidian label map from converted markdown files.

The output schema is intentionally small:
{
  "<name of block>": {"file": "...", "block_id": "^..."}
}

The script infers the name from the nearest preceding callout title, heading,
or paragraph. Hand-edit the resulting JSON when a source has better names such
as LaTeX labels, HTML ids, PDF page anchors, or image regions.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path


BLOCK_ID_RE = re.compile(r"^\^([A-Za-z0-9-]+)\s*$")
CALLOUT_RE = re.compile(r"^>\s*\[![^\]]+\]\s*(.*)$")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")


def clean_name(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), text)
    text = re.sub(r"[*_`~]", "", text)
    text = re.sub(r"\$+", "", text)
    text = text.strip(" >#:-")
    return text


def fallback_name(block_id: str) -> str:
    return block_id.lstrip("^")


def infer_name(lines: list[str], block_line_index: int, block_id: str) -> str:
    for i in range(block_line_index - 1, -1, -1):
        line = lines[i].strip()
        if not line:
            continue
        if not line.startswith(">"):
            break

        callout = CALLOUT_RE.match(line)
        if callout:
            name = clean_name(callout.group(1))
            return name or fallback_name(block_id)

    for i in range(block_line_index - 1, -1, -1):
        line = lines[i].strip()
        if not line:
            continue

        callout = CALLOUT_RE.match(line)
        if callout:
            name = clean_name(callout.group(1))
            return name or fallback_name(block_id)

        heading = HEADING_RE.match(line)
        if heading:
            name = clean_name(heading.group(1))
            return name or fallback_name(block_id)

        if line.startswith("$$"):
            return fallback_name(block_id)

        if line.startswith(">"):
            name = clean_name(line.lstrip(">"))
            if name and not name.startswith("[!"):
                return name
            continue

        if not line.startswith("```") and not line.startswith("$$"):
            name = clean_name(line)
            if name:
                return name[:120]

    return fallback_name(block_id)


def unique_key(mapping: dict[str, dict[str, object]], key: str, block_id: str) -> str:
    if key not in mapping:
        return key

    base = key or fallback_name(block_id)
    suffix = block_id.lstrip("^")
    candidate = f"{base} ({suffix})"
    n = 2
    while candidate in mapping:
        candidate = f"{base} ({suffix}-{n})"
        n += 1
    return candidate


def iter_markdown_files(patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            files.extend(Path(match) for match in matches)
        else:
            files.append(Path(pattern))
    return sorted({path for path in files if path.suffix.lower() == ".md" and path.exists()})


def build_map(files: list[Path], base_dir: Path | None = None) -> dict[str, dict[str, object]]:
    mapping: dict[str, dict[str, object]] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        display_file = path.name if base_dir is None else path.relative_to(base_dir).as_posix()

        for i, line in enumerate(lines):
            match = BLOCK_ID_RE.match(line.strip())
            if not match:
                continue
            block_id = f"^{match.group(1)}"
            name = infer_name(lines, i, block_id)
            name = unique_key(mapping, name, block_id)
            mapping[name] = {
                "file": display_file,
                "block_id": block_id,
            }
    return mapping


def main() -> int:
    parser = argparse.ArgumentParser(description="Build output/label_map.json from Obsidian markdown block IDs.")
    parser.add_argument("patterns", nargs="+", help="Markdown files or glob patterns, e.g. output/**/*.md")
    parser.add_argument("--output", "-o", default="output/label_map.json", help="Output JSON path")
    parser.add_argument("--base-dir", help="Directory used for relative file paths in the JSON")
    args = parser.parse_args()

    files = iter_markdown_files(args.patterns)
    base_dir = Path(args.base_dir).resolve() if args.base_dir else None
    mapping = build_map(files, base_dir)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(mapping)} blocks to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
