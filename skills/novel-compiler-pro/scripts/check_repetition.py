#!/usr/bin/env python3
"""Detect repeated passages, openings, endings, and high-frequency stock phrases."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from difflib import SequenceMatcher

from common import (
    exit_code_for_status,
    iter_chapter_files,
    markdown_table,
    parse_chapter_filename,
    print_json,
    read_text,
    root_path,
    status_from_issues,
    write_text,
)


DEFAULT_STOCK_PATTERNS = [
    "他意识到",
    "她意识到",
    "他终于意识到",
    "她终于意识到",
    "沉默了片刻",
    "没有说话",
    "风声",
    "夜色",
    "仿佛整个世界",
    "某种意义上",
    "一切才刚刚开始",
]


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，。！？；：“”‘’、,.!?;:\"'()\[\]（）【】《》\-—…]", "", text)
    return text


def first_nonempty_paragraph(text: str) -> str:
    for para in re.split(r"\n\s*\n", text.strip()):
        clean = para.strip()
        if clean:
            return clean
    return ""


def last_nonempty_paragraph(text: str) -> str:
    for para in reversed(re.split(r"\n\s*\n", text.strip())):
        clean = para.strip()
        if clean:
            return clean
    return ""


def chunks(text: str, size: int, step: int) -> set[str]:
    if len(text) < size:
        return set()
    return {text[i : i + size] for i in range(0, len(text) - size + 1, step)}


def similarity(a: str, b: str) -> float:
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    return SequenceMatcher(None, a_norm[:300], b_norm[:300]).ratio()


def build_report(root, chunk_size: int, step: int, opening_threshold: float, ending_threshold: float, stock_limit: int) -> dict:
    chapter_entries = []
    issues = []
    chunk_map: dict[str, list[str]] = defaultdict(list)

    for path in iter_chapter_files(root):
        parsed = parse_chapter_filename(path)
        text = read_text(path)
        chapter_id = parsed["num"] if parsed else path.name
        normalized = normalize_text(text)
        opening = first_nonempty_paragraph(text)
        ending = last_nonempty_paragraph(text)
        stock_counts = {pattern: text.count(pattern) for pattern in DEFAULT_STOCK_PATTERNS if text.count(pattern)}

        for chunk in chunks(normalized, chunk_size, step):
            chunk_map[chunk].append(chapter_id)

        chapter_entries.append(
            {
                "chapter_id": chapter_id,
                "filename": path.name,
                "opening": opening,
                "ending": ending,
                "stock_counts": stock_counts,
                "chars": len(normalized),
            }
        )

        for pattern, count in stock_counts.items():
            if count > stock_limit:
                issues.append(
                    {
                        "severity": "中",
                        "type": "stock_phrase",
                        "location": path.name,
                        "message": f"Stock phrase appears {count} times: {pattern}",
                        "evidence": pattern,
                    }
                )

    seen_pairs = set()
    for chunk, chapter_ids in chunk_map.items():
        unique = sorted(set(chapter_ids))
        if len(unique) < 2:
            continue
        key = tuple(unique[:5])
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        issues.append(
            {
                "severity": "高",
                "type": "repeated_passage",
                "location": ", ".join(unique[:5]),
                "message": f"Repeated normalized passage of {chunk_size} chars appears across chapters.",
                "evidence": chunk[:80],
            }
        )

    for idx, left in enumerate(chapter_entries):
        for right in chapter_entries[idx + 1 :]:
            open_score = similarity(left["opening"], right["opening"])
            if open_score >= opening_threshold:
                issues.append(
                    {
                        "severity": "中",
                        "type": "similar_opening",
                        "location": f"{left['chapter_id']} / {right['chapter_id']}",
                        "message": f"Opening paragraphs are {open_score:.0%} similar.",
                        "evidence": left["opening"][:80],
                    }
                )
            end_score = similarity(left["ending"], right["ending"])
            if end_score >= ending_threshold:
                issues.append(
                    {
                        "severity": "中",
                        "type": "similar_ending",
                        "location": f"{left['chapter_id']} / {right['chapter_id']}",
                        "message": f"Ending paragraphs are {end_score:.0%} similar.",
                        "evidence": left["ending"][:80],
                    }
                )

    status = status_from_issues(issues)
    return {
        "status": status,
        "root": str(root),
        "chapter_count": len(chapter_entries),
        "issues": issues,
        "settings": {
            "chunk_size": chunk_size,
            "step": step,
            "opening_threshold": opening_threshold,
            "ending_threshold": ending_threshold,
            "stock_limit": stock_limit,
        },
    }


def to_markdown(report: dict) -> str:
    issue_rows = [
        [idx + 1, issue["severity"], issue["type"], issue["location"], issue["message"], issue.get("evidence", "")]
        for idx, issue in enumerate(report["issues"])
    ]
    if not issue_rows:
        issue_rows = [["-", "-", "-", "-", "No repetition issues found.", ""]]

    return "\n\n".join(
        [
            "# Repetition Report",
            f"- Status: {report['status']}",
            f"- Chapter count: {report['chapter_count']}",
            "## Settings",
            markdown_table(
                ["Chunk Size", "Step", "Opening Threshold", "Ending Threshold", "Stock Limit"],
                [[
                    report["settings"]["chunk_size"],
                    report["settings"]["step"],
                    report["settings"]["opening_threshold"],
                    report["settings"]["ending_threshold"],
                    report["settings"]["stock_limit"],
                ]],
            ),
            "## Issues",
            markdown_table(["#", "Severity", "Type", "Location", "Message", "Evidence"], issue_rows),
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Novel project root.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--chunk-size", type=int, default=80, help="Normalized character chunk size for exact duplicate detection.")
    parser.add_argument("--step", type=int, default=20, help="Sliding window step for duplicate detection.")
    parser.add_argument("--opening-threshold", type=float, default=0.82, help="Similarity threshold for opening paragraphs.")
    parser.add_argument("--ending-threshold", type=float, default=0.82, help="Similarity threshold for ending paragraphs.")
    parser.add_argument("--stock-limit", type=int, default=3, help="Warn when a stock phrase appears more than this per chapter.")
    parser.add_argument("--write-report", nargs="?", const="reports/repetition_report.md", help="Write Markdown report to path.")
    args = parser.parse_args()

    root = root_path(args.root)
    report = build_report(root, args.chunk_size, args.step, args.opening_threshold, args.ending_threshold, args.stock_limit)
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
