#!/usr/bin/env python3
"""Shared helpers for novel-compiler-pro scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REQUIRED_DIRS = [
    "input",
    "memory",
    "canon",
    "specs",
    "planning",
    "manuscript",
    "manuscript/chapters",
    "reports",
    "final",
]

OPTIONAL_DIRS = ["market"]

REQUIRED_FILES = {
    "input": [
        "project_brief.md",
        "world_seed.md",
        "character_seed.md",
        "plot_seed.md",
        "style_seed.md",
        "constraints.md",
        "reference_fragments.md",
    ],
    "memory": [
        "smart_state.md",
        "novel_state.md",
        "recent_chapter_summaries.md",
        "next_chapter_task.md",
        "style_anchor.md",
        "reader_promise.md",
        "open_threads.md",
        "retrieval_index.md",
        "repetition_guard.md",
        "rolling_100k_state.md",
    ],
    "canon": [
        "world.md",
        "characters.md",
        "timeline.md",
        "locations.md",
        "organizations.md",
        "terminology.md",
        "relationship_map.md",
        "foreshadowing.md",
        "unresolved_questions.md",
        "style_guide.md",
        "naming_rules.md",
    ],
    "specs": [
        "constitution.md",
        "specification.md",
        "clarifications.md",
        "creative_plan.md",
        "tasks.md",
        "analysis.md",
    ],
    "planning": [
        "premise.md",
        "theme.md",
        "book_plan.md",
        "plot_spine.md",
        "part_plan.md",
        "volume_plan.md",
        "chapter_plan.md",
        "scene_plan.md",
        "rolling_100k_plan.md",
    ],
    "reports": [
        "compile_log.md",
        "consistency_report.md",
        "character_arc_report.md",
        "foreshadowing_report.md",
        "pacing_report.md",
        "revision_report.md",
        "style_report.md",
        "repetition_report.md",
        "milestone_100k_report.md",
        "final_consistency_report.md",
        "final_report.md",
    ],
    "final": ["final_novel.md"],
}

CHAPTER_RE = re.compile(
    r"^(?P<num>\d{4})_(?P<part>[^_]+)_(?P<volume>[^_]+)_(?P<volume_title>[^_]+)_(?P<chapter>.+)\.txt$"
)

FORBIDDEN_MARKERS = [
    ("TODO", "TODO marker"),
    ("FIXME", "FIXME marker"),
    ("[说明]", "meta note"),
    ("[注", "bracketed note"),
    ("（注：", "inline note"),
    ("作者注", "author note"),
    ("写作分析", "writing analysis residue"),
    ("本章功能", "chapter-plan residue"),
    ("必须包含", "chapter-plan residue"),
    ("必须避免", "chapter-plan residue"),
]


def root_path(value: str | None) -> Path:
    return Path(value or ".").resolve()


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def chapter_dir(root: Path) -> Path:
    return root / "manuscript" / "chapters"


def iter_chapter_files(root: Path) -> list[Path]:
    directory = chapter_dir(root)
    if not directory.exists():
        return []
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".txt")


def parse_chapter_filename(path: Path) -> dict[str, Any] | None:
    match = CHAPTER_RE.match(path.name)
    if not match:
        return None
    data = match.groupdict()
    data["num_int"] = int(data["num"])
    data["filename"] = path.name
    return data


def count_text_units(text: str) -> dict[str, int]:
    chars_no_space = sum(1 for ch in text if not ch.isspace())
    cjk_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    latin_words = len(re.findall(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*", text))
    return {
        "chars_no_space": chars_no_space,
        "cjk_chars": cjk_chars,
        "latin_words": latin_words,
        "estimated_units": cjk_chars + latin_words,
    }


def find_forbidden_markers(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for marker, label in FORBIDDEN_MARKERS:
            if marker in line:
                findings.append(
                    {
                        "line": line_no,
                        "marker": marker,
                        "label": label,
                        "excerpt": line.strip()[:120],
                    }
                )
    return findings


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ").strip()

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def status_from_issues(issues: list[dict[str, Any]]) -> str:
    if any(item.get("severity") == "高" for item in issues):
        return "FAIL"
    if issues:
        return "WARN"
    return "PASS"


def exit_code_for_status(status: str) -> int:
    return 1 if status == "FAIL" else 0
