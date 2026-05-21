#!/usr/bin/env python3
"""Validate chapter filenames, numbering, word counts, and draft residue."""

from __future__ import annotations

import argparse
from collections import Counter

from common import (
    count_text_units,
    exit_code_for_status,
    find_forbidden_markers,
    iter_chapter_files,
    markdown_table,
    parse_chapter_filename,
    print_json,
    read_text,
    root_path,
    status_from_issues,
    write_text,
)


def build_report(root, min_units: int | None, max_units: int | None) -> dict:
    files = iter_chapter_files(root)
    chapters = []
    issues = []

    for path in files:
        parsed = parse_chapter_filename(path)
        text = read_text(path)
        counts = count_text_units(text)
        entry = {
            "filename": path.name,
            "valid_filename": parsed is not None,
            "metadata": parsed,
            "counts": counts,
        }
        chapters.append(entry)

        if parsed is None:
            issues.append({"severity": "高", "type": "filename", "location": path.name, "message": "Filename does not match 全局编号_部_卷_卷标题_章节名.txt."})

        if min_units is not None and counts["chars_no_space"] < min_units:
            issues.append({"severity": "中", "type": "word_count", "location": path.name, "message": f"Chapter is below minimum {min_units} chars."})
        if max_units is not None and counts["chars_no_space"] > max_units:
            issues.append({"severity": "中", "type": "word_count", "location": path.name, "message": f"Chapter is above maximum {max_units} chars."})

        for finding in find_forbidden_markers(text):
            issues.append(
                {
                    "severity": "高",
                    "type": "draft_residue",
                    "location": f"{path.name}:{finding['line']}",
                    "message": f"{finding['label']}: {finding['marker']}",
                    "evidence": finding["excerpt"],
                }
            )

    valid_numbers = [item["metadata"]["num_int"] for item in chapters if item["metadata"]]
    counts = Counter(valid_numbers)
    for num, amount in sorted(counts.items()):
        if amount > 1:
            issues.append({"severity": "高", "type": "numbering", "location": f"{num:04d}", "message": "Duplicate global chapter number."})

    unique = sorted(counts)
    if unique:
        expected = list(range(unique[0], unique[-1] + 1))
        missing = [num for num in expected if num not in counts]
        if unique[0] != 1:
            issues.append({"severity": "中", "type": "numbering", "location": f"{unique[0]:04d}", "message": "First chapter number is not 0001."})
        if missing:
            issues.append({"severity": "中", "type": "numbering", "location": ",".join(f"{num:04d}" for num in missing[:20]), "message": "Global chapter numbering has gaps."})

    status = status_from_issues(issues)
    return {
        "status": status,
        "root": str(root),
        "chapter_count": len(files),
        "valid_chapter_count": sum(1 for item in chapters if item["valid_filename"]),
        "chapters": chapters,
        "issues": issues,
    }


def to_markdown(report: dict) -> str:
    chapter_rows = []
    for item in sorted(report["chapters"], key=lambda c: (c["metadata"]["num_int"] if c["metadata"] else 999999, c["filename"])):
        meta = item["metadata"] or {}
        chapter_rows.append(
            [
                meta.get("num", "-"),
                item["filename"],
                "yes" if item["valid_filename"] else "no",
                item["counts"]["chars_no_space"],
                item["counts"]["estimated_units"],
            ]
        )

    issue_rows = [
        [idx + 1, issue["severity"], issue["type"], issue["location"], issue["message"], issue.get("evidence", "")]
        for idx, issue in enumerate(report["issues"])
    ]
    if not chapter_rows:
        chapter_rows = [["-", "No chapter files found.", "-", 0, 0]]
    if not issue_rows:
        issue_rows = [["-", "-", "-", "-", "No chapter gate issues found.", ""]]

    return "\n\n".join(
        [
            "# Chapter Gate Report",
            f"- Status: {report['status']}",
            f"- Chapter files: {report['chapter_count']}",
            f"- Valid chapter files: {report['valid_chapter_count']}",
            "## Chapters",
            markdown_table(["No.", "Filename", "Valid", "Chars", "Units"], chapter_rows),
            "## Issues",
            markdown_table(["#", "Severity", "Type", "Location", "Message", "Evidence"], issue_rows),
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Novel project root.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--min-chars", type=int, default=None, help="Warn if chapter chars_no_space is below this value.")
    parser.add_argument("--max-chars", type=int, default=None, help="Warn if chapter chars_no_space is above this value.")
    parser.add_argument("--write-report", nargs="?", const="reports/chapter_gate_report.md", help="Write Markdown report to path.")
    args = parser.parse_args()

    root = root_path(args.root)
    report = build_report(root, args.min_chars, args.max_chars)
    if args.json:
        print_json(report)
    else:
        output = to_markdown(report)
        print(output)
        if args.write_report:
            write_text(root / args.write_report, output)
    return exit_code_for_status(report["status"])


if __name__ == "__main__":
    raise SystemExit(main())
