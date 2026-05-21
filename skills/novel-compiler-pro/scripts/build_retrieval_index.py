#!/usr/bin/env python3
"""Build a lightweight retrieval index from chapters and canon terms."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict

from common import count_text_units, iter_chapter_files, markdown_table, parse_chapter_filename, print_json, read_text, root_path, write_text


def headings(path):
    if not path.is_file():
        return []
    found = []
    for line in read_text(path).splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            value = match.group(1).strip()
            if value and value not in {"人物名", "地点名", "组织名"}:
                found.append(value)
    return found


def table_first_column(path):
    if not path.is_file():
        return []
    values = []
    for line in read_text(path).splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if parts and parts[0] not in {"术语", "ID", ""}:
            values.append(parts[0])
    return values


def known_keywords(root):
    items = []
    sources = [
        ("character", headings(root / "canon" / "characters.md")),
        ("location", headings(root / "canon" / "locations.md")),
        ("organization", headings(root / "canon" / "organizations.md")),
        ("term", table_first_column(root / "canon" / "terminology.md")),
        ("foreshadowing", table_first_column(root / "canon" / "foreshadowing.md")),
    ]
    for kind, values in sources:
        for value in values:
            if 2 <= len(value) <= 30:
                items.append((value, kind))
    return sorted(set(items))


def build(root, output_rel: str, write_meta: bool) -> dict:
    chapters = []
    index = defaultdict(lambda: {"type": set(), "chapters": set(), "notes": set()})
    keywords = known_keywords(root)

    for path in iter_chapter_files(root):
        parsed = parse_chapter_filename(path)
        if not parsed:
            continue
        text = read_text(path)
        counts = count_text_units(text)
        chapter_id = parsed["num"]
        matched = []

        structural_terms = [
            (parsed["part"], "part"),
            (parsed["volume"], "volume"),
            (parsed["volume_title"], "volume_title"),
            (parsed["chapter"], "chapter_title"),
        ]
        for value, kind in structural_terms + keywords:
            if value and (value in text or kind in {"part", "volume", "volume_title", "chapter_title"}):
                key = value.strip()
                index[key]["type"].add(kind)
                index[key]["chapters"].add(chapter_id)
                index[key]["notes"].add(parsed["filename"])
                matched.append({"keyword": key, "type": kind})

        excerpt = re.sub(r"\s+", "", text)[:120]
        meta = {
            "chapter": chapter_id,
            "filename": parsed["filename"],
            "part": parsed["part"],
            "volume": parsed["volume"],
            "volume_title": parsed["volume_title"],
            "chapter_title": parsed["chapter"],
            "counts": counts,
            "matched_keywords": matched,
            "opening_excerpt": excerpt,
        }
        chapters.append(meta)
        if write_meta:
            meta_path = root / "memory" / "retrieval" / "chapter_meta" / f"{path.stem}.meta.json"
            write_text(meta_path, json.dumps(meta, ensure_ascii=False, indent=2) + "\n")

    rows = []
    for keyword, data in sorted(index.items(), key=lambda item: (min(item[1]["chapters"]) if item[1]["chapters"] else "9999", item[0])):
        rows.append(
            [
                keyword,
                ",".join(sorted(data["type"])),
                ", ".join(sorted(data["chapters"])),
                "; ".join(sorted(data["notes"])[:3]),
            ]
        )
    if not rows:
        rows = [["-", "-", "-", "No valid chapter files found or no keywords matched."]]

    markdown = "\n\n".join(
        [
            "# Retrieval Index",
            "Lightweight index generated from chapter filenames, canon terms, and chapter text.",
            markdown_table(["Keyword", "Type", "Related Chapters", "Notes"], rows),
        ]
    ) + "\n"
    output_path = root / output_rel
    write_text(output_path, markdown)
    return {
        "status": "PASS",
        "output": str(output_path),
        "chapter_count": len(chapters),
        "keyword_count": len(index),
        "meta_written": write_meta,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Novel project root.")
    parser.add_argument("--output", default="memory/retrieval_index.md", help="Output path relative to root.")
    parser.add_argument("--no-meta", action="store_true", help="Do not write memory/retrieval/chapter_meta/*.json.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown summary.")
    args = parser.parse_args()

    result = build(root_path(args.root), args.output, not args.no_meta)
    if args.json:
        print_json(result)
    else:
        print("# Retrieval Build\n")
        print(f"- Status: {result['status']}")
        print(f"- Output: `{result['output']}`")
        print(f"- Chapters indexed: {result['chapter_count']}")
        print(f"- Keywords indexed: {result['keyword_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
