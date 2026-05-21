#!/usr/bin/env python3
"""Build a mechanical 100k-word/character block map for long-novel milestone review."""

from __future__ import annotations

import argparse
from collections import defaultdict

from common import count_text_units, iter_chapter_files, markdown_table, parse_chapter_filename, print_json, read_text, root_path, write_text


def build_report(root, block_size: int) -> dict:
    chapters = []
    blocks: dict[int, dict] = defaultdict(lambda: {"chapters": [], "chars": 0, "units": 0})
    cumulative = 0

    for path in iter_chapter_files(root):
        parsed = parse_chapter_filename(path)
        if not parsed:
            continue
        text = read_text(path)
        counts = count_text_units(text)
        start_total = cumulative + 1
        cumulative += counts["chars_no_space"]
        end_total = cumulative
        block_start = max(1, (start_total - 1) // block_size + 1)
        block_end = max(1, (end_total - 1) // block_size + 1)

        entry = {
            "num": parsed["num"],
            "filename": path.name,
            "part": parsed["part"],
            "volume": parsed["volume"],
            "volume_title": parsed["volume_title"],
            "chapter": parsed["chapter"],
            "chars": counts["chars_no_space"],
            "units": counts["estimated_units"],
            "cumulative_start": start_total,
            "cumulative_end": end_total,
            "blocks": list(range(block_start, block_end + 1)),
        }
        chapters.append(entry)
        for block_no in entry["blocks"]:
            block_start = (block_no - 1) * block_size + 1
            block_end = block_no * block_size
            overlap = max(0, min(end_total, block_end) - max(start_total, block_start) + 1)
            unit_overlap = round(counts["estimated_units"] * (overlap / max(1, counts["chars_no_space"])))
            blocks[block_no]["chapters"].append(parsed["num"])
            blocks[block_no]["chars"] += overlap
            blocks[block_no]["units"] += unit_overlap

    current_block = max(1, (max(cumulative, 1) - 1) // block_size + 1)
    next_boundary = current_block * block_size
    chars_to_next = max(0, next_boundary - cumulative)
    completed_blocks = max(0, cumulative // block_size)

    return {
        "status": "PASS",
        "root": str(root),
        "block_size": block_size,
        "total_chars": cumulative,
        "chapter_count": len(chapters),
        "current_block": current_block,
        "completed_blocks": completed_blocks,
        "next_boundary": next_boundary,
        "chars_to_next_boundary": chars_to_next,
        "blocks": [
            {
                "block": block_no,
                "range": f"{(block_no - 1) * block_size + 1}-{block_no * block_size}",
                "chapter_count": len(data["chapters"]),
                "chapters": ", ".join(data["chapters"]),
                "chars": data["chars"],
                "units": data["units"],
            }
            for block_no, data in sorted(blocks.items())
        ],
        "chapters": chapters,
    }


def to_markdown(report: dict) -> str:
    block_rows = [
        [item["block"], item["range"], item["chapter_count"], item["chapters"], item["chars"], item["units"]]
        for item in report["blocks"]
    ]
    if not block_rows:
        block_rows = [["-", "-", 0, "No valid chapter files found.", 0, 0]]

    chapter_rows = [
        [
            item["num"],
            item["filename"],
            item["cumulative_start"],
            item["cumulative_end"],
            ",".join(str(block) for block in item["blocks"]),
        ]
        for item in report["chapters"]
    ]
    if not chapter_rows:
        chapter_rows = [["-", "No valid chapter files found.", 0, 0, "-"]]

    return "\n\n".join(
        [
            "# 100k Milestone Report",
            f"- Status: {report['status']}",
            f"- Block size: {report['block_size']}",
            f"- Total chars no space: {report['total_chars']}",
            f"- Chapter count: {report['chapter_count']}",
            f"- Completed blocks: {report['completed_blocks']}",
            f"- Current block: {report['current_block']}",
            f"- Next boundary: {report['next_boundary']}",
            f"- Chars to next boundary: {report['chars_to_next_boundary']}",
            "## Block Map",
            markdown_table(["Block", "Range", "Chapter Count", "Chapters", "Chars", "Units"], block_rows),
            "## Chapter Boundary Map",
            markdown_table(["No.", "Filename", "Cumulative Start", "Cumulative End", "Blocks"], chapter_rows),
            "## Semantic Review To Fill",
            "### What Has Happened",
            "### Architecture Comparison",
            "### Drift / Repetition Risks",
            "### Next 100k Generation Brief",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Novel project root.")
    parser.add_argument("--block-size", type=int, default=100000, help="Milestone size in chars_no_space.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--write-report", nargs="?", const="reports/milestone_100k_report.md", help="Write Markdown report to path.")
    args = parser.parse_args()

    root = root_path(args.root)
    report = build_report(root, args.block_size)
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
