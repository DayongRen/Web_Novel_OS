#!/usr/bin/env python3
"""Assemble valid chapter files into final/final_novel.md."""

from __future__ import annotations

import argparse
import re

from common import iter_chapter_files, parse_chapter_filename, print_json, read_text, root_path, write_text


def extract_title(root) -> str:
    candidates = [
        (root / "specs" / "specification.md", r"## Title\s+(.+?)(?:\n## |\Z)"),
        (root / "input" / "project_brief.md", r"## 小说暂定名\s+(.+?)(?:\n## |\Z)"),
    ]
    for path, pattern in candidates:
        if not path.is_file():
            continue
        text = read_text(path)
        match = re.search(pattern, text, flags=re.S)
        if match:
            value = "\n".join(line.strip() for line in match.group(1).splitlines() if line.strip())
            if value and not value.startswith("##"):
                return value.splitlines()[0]
    return "Final Novel"


def assemble(root, output_rel: str) -> dict:
    valid = []
    invalid = []
    for path in iter_chapter_files(root):
        parsed = parse_chapter_filename(path)
        if parsed:
            valid.append((parsed["num_int"], parsed, path))
        else:
            invalid.append(path.name)
    valid.sort(key=lambda item: item[0])

    if not valid:
        return {"status": "FAIL", "message": "No valid chapter files found.", "invalid_files": invalid}

    lines = [f"# {extract_title(root)}", ""]
    current_part = None
    current_volume_key = None
    total_chars = 0

    for _, meta, path in valid:
        if meta["part"] != current_part:
            current_part = meta["part"]
            current_volume_key = None
            lines.extend([f"# {current_part}", ""])
        volume_key = (meta["volume"], meta["volume_title"])
        if volume_key != current_volume_key:
            current_volume_key = volume_key
            lines.extend([f"## {meta['volume']}：{meta['volume_title']}", ""])
        lines.extend([f"### {meta['chapter']}", ""])
        body = read_text(path).strip()
        total_chars += len("".join(ch for ch in body if not ch.isspace()))
        lines.extend([body, ""])

    output_path = root / output_rel
    write_text(output_path, "\n".join(lines).rstrip() + "\n")
    return {
        "status": "PASS",
        "output": str(output_path),
        "chapter_count": len(valid),
        "invalid_files": invalid,
        "chars_no_space": total_chars,
    }


def to_markdown(result: dict) -> str:
    lines = [
        "# Final Assembly Report",
        f"- Status: {result['status']}",
    ]
    if result["status"] == "PASS":
        lines.extend(
            [
                f"- Output: `{result['output']}`",
                f"- Chapter count: {result['chapter_count']}",
                f"- Chars no space: {result['chars_no_space']}",
            ]
        )
    else:
        lines.append(f"- Message: {result['message']}")
    if result.get("invalid_files"):
        lines.extend(["", "## Ignored Invalid Files", *[f"- `{name}`" for name in result["invalid_files"]]])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Novel project root.")
    parser.add_argument("--output", default="final/final_novel.md", help="Output path relative to root.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--write-report", nargs="?", const="reports/final_assembly_report.md", help="Write Markdown report to path.")
    args = parser.parse_args()

    root = root_path(args.root)
    result = assemble(root, args.output)
    if args.json:
        print_json(result)
    else:
        output = to_markdown(result)
        print(output)
        if args.write_report:
            write_text(root / args.write_report, output)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
