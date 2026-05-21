#!/usr/bin/env python3
"""Count words/characters for chapter files and optional final manuscript."""

from __future__ import annotations

import argparse

from common import count_text_units, iter_chapter_files, markdown_table, parse_chapter_filename, print_json, read_text, root_path, write_text


def build_report(root, include_final: bool) -> dict:
    rows = []
    totals = {"chars_no_space": 0, "cjk_chars": 0, "latin_words": 0, "estimated_units": 0}

    for path in iter_chapter_files(root):
        parsed = parse_chapter_filename(path)
        counts = count_text_units(read_text(path))
        for key in totals:
            totals[key] += counts[key]
        rows.append(
            {
                "num": parsed["num"] if parsed else "",
                "filename": path.name,
                "valid_filename": parsed is not None,
                **counts,
            }
        )

    final_counts = None
    final_path = root / "final" / "final_novel.md"
    if include_final and final_path.is_file():
        final_counts = count_text_units(read_text(final_path))

    return {
        "root": str(root),
        "chapter_count": len(rows),
        "chapters": rows,
        "totals": totals,
        "final": final_counts,
    }


def to_markdown(report: dict) -> str:
    rows = [
        [item["num"] or "-", item["filename"], item["chars_no_space"], item["cjk_chars"], item["latin_words"], item["estimated_units"]]
        for item in report["chapters"]
    ]
    if not rows:
        rows = [["-", "No chapter files found.", 0, 0, 0, 0]]

    sections = [
        "# Word Count Report",
        f"- Chapter count: {report['chapter_count']}",
        f"- Total chars no space: {report['totals']['chars_no_space']}",
        f"- Total estimated units: {report['totals']['estimated_units']}",
        "## Chapters",
        markdown_table(["No.", "Filename", "Chars", "CJK", "Latin Words", "Units"], rows),
    ]
    if report["final"] is not None:
        sections.extend(
            [
                "## Final Manuscript",
                markdown_table(
                    ["Chars", "CJK", "Latin Words", "Units"],
                    [[
                        report["final"]["chars_no_space"],
                        report["final"]["cjk_chars"],
                        report["final"]["latin_words"],
                        report["final"]["estimated_units"],
                    ]],
                ),
            ]
        )
    return "\n\n".join(sections) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Novel project root.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--include-final", action="store_true", help="Also count final/final_novel.md.")
    parser.add_argument("--write-report", nargs="?", const="reports/word_count_report.md", help="Write Markdown report to path.")
    args = parser.parse_args()

    root = root_path(args.root)
    report = build_report(root, args.include_final)
    if args.json:
        print_json(report)
    else:
        output = to_markdown(report)
        print(output)
        if args.write_report:
            write_text(root / args.write_report, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
