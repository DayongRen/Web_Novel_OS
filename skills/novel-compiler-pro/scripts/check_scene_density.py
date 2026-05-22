#!/usr/bin/env python3
"""Check scene-driven prose density and anti-AI summary patterns."""

from __future__ import annotations

import argparse
import re

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


BANNED_PATTERNS = [
    "这不仅是",
    "更是",
    "从这一刻起",
    "终于意识到",
    "内心深处知道",
    "真正的问题",
    "这象征着",
    "这代表了",
    "某种意义上",
    "他不知道的是",
    "她不知道的是",
    "一切都变了",
    "这标志着",
    "命运的齿轮",
    "故事由此展开",
    "this was not only",
    "but also",
    "from this moment",
    "finally realized",
    "deep down",
    "the real problem",
    "everything had changed",
]

ABSTRACT_EMOTION_LABELS = [
    "愤怒",
    "悲伤",
    "震惊",
    "感动",
    "孤独",
    "绝望",
    "迷茫",
    "坚定",
    "疲惫",
    "痛苦",
    "紧张",
    "不安",
    "害怕",
    "恐惧",
    "焦虑",
    "崩溃",
]

ACTION_MARKERS = [
    "走",
    "跑",
    "推",
    "拉",
    "按",
    "放",
    "拿",
    "递",
    "摔",
    "砸",
    "撕",
    "折",
    "拖",
    "贴",
    "敲",
    "撞",
    "抬",
    "低",
    "转身",
    "回头",
    "停",
    "站",
    "坐",
    "弯腰",
    "抬头",
    "开门",
    "关门",
    "签",
    "翻",
    "扣",
    "压",
    "抖",
    "攥",
    "捏",
]

CONCRETE_MARKERS = [
    "门",
    "桌",
    "椅",
    "纸",
    "信",
    "箱",
    "灯",
    "窗",
    "杯",
    "手",
    "指",
    "鞋",
    "衣",
    "墙",
    "地",
    "车",
    "电话",
    "屏幕",
    "合同",
    "标签",
    "胶带",
    "声音",
    "气味",
    "光",
    "影",
]

DIALOGUE_RE = re.compile(r"[“\"].{1,120}?[”\"]")


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def first_para(text: str) -> str:
    items = paragraphs(text)
    return items[0] if items else ""


def last_para(text: str) -> str:
    items = paragraphs(text)
    return items[-1] if items else ""


def contains_any(text: str, markers: list[str]) -> bool:
    lower = text.lower()
    return any(marker.lower() in lower for marker in markers)


def count_any(text: str, markers: list[str]) -> int:
    lower = text.lower()
    return sum(lower.count(marker.lower()) for marker in markers)


def early_text(text: str, limit: int) -> str:
    return compact(text)[:limit]


def visible_event_windows(text: str, window_size: int) -> tuple[int, int]:
    body = compact(text)
    if not body:
        return 0, 0
    windows = [body[i : i + window_size] for i in range(0, len(body), window_size)]
    failed = 0
    for window in windows:
        if not (DIALOGUE_RE.search(window) or contains_any(window, ACTION_MARKERS)):
            failed += 1
    return len(windows), failed


def build_report(root, early_limit: int, window_size: int, emotion_limit: int) -> dict:
    issues = []
    chapters = []

    for path in iter_chapter_files(root):
        parsed = parse_chapter_filename(path)
        chapter_id = parsed["num"] if parsed else path.name
        text = read_text(path)
        first = first_para(text)
        last = last_para(text)
        fail_count = 0
        chapter_issues = []

        if not (contains_any(first, ACTION_MARKERS) or contains_any(first, CONCRETE_MARKERS) or DIALOGUE_RE.search(first)):
            fail_count += 1
            chapter_issues.append(
                {
                    "severity": "中",
                    "type": "weak_opening",
                    "location": path.name,
                    "message": "First paragraph lacks a concrete image, object, action, or dialogue.",
                    "evidence": first[:100],
                }
            )

        if not DIALOGUE_RE.search(early_text(text, early_limit)):
            fail_count += 1
            chapter_issues.append(
                {
                    "severity": "中",
                    "type": "late_dialogue",
                    "location": path.name,
                    "message": f"No dialogue appears within the first {early_limit} compact characters.",
                    "evidence": early_text(text, 100),
                }
            )

        window_total, window_failed = visible_event_windows(text, window_size)
        if window_failed:
            fail_count += 1
            chapter_issues.append(
                {
                    "severity": "中",
                    "type": "low_visible_event_density",
                    "location": path.name,
                    "message": f"{window_failed}/{window_total} text windows lack obvious visible event markers.",
                    "evidence": "",
                }
            )

        banned_found = [pattern for pattern in BANNED_PATTERNS if pattern.lower() in text.lower()]
        if banned_found:
            fail_count += 1
            chapter_issues.append(
                {
                    "severity": "高",
                    "type": "banned_ai_style_pattern",
                    "location": path.name,
                    "message": "Banned commentary-style pattern appears.",
                    "evidence": ", ".join(banned_found[:8]),
                }
            )

        emotion_count = count_any(text, ABSTRACT_EMOTION_LABELS)
        if emotion_count > emotion_limit:
            fail_count += 1
            chapter_issues.append(
                {
                    "severity": "中",
                    "type": "abstract_emotion_overuse",
                    "location": path.name,
                    "message": f"Abstract emotion labels appear {emotion_count} times; convert labels into behavior where possible.",
                    "evidence": "",
                }
            )

        if contains_any(last, BANNED_PATTERNS) or (
            contains_any(last, ["明白", "意义", "象征", "代表", "命运", "一切"])
            and not (DIALOGUE_RE.search(last) or contains_any(last, ACTION_MARKERS) or contains_any(last, CONCRETE_MARKERS))
        ):
            fail_count += 1
            chapter_issues.append(
                {
                    "severity": "中",
                    "type": "summary_ending",
                    "location": path.name,
                    "message": "Ending reads like a summary or thematic conclusion rather than image/action/dialogue.",
                    "evidence": last[:100],
                }
            )

        if fail_count > 2:
            issues.append(
                {
                    "severity": "高",
                    "type": "scene_density_failure",
                    "location": path.name,
                    "message": f"Chapter failed {fail_count} scene-density checks; run Anti-AI Rewriter before continuing.",
                    "evidence": "",
                }
            )

        issues.extend(chapter_issues)
        chapters.append({"chapter_id": chapter_id, "filename": path.name, "fail_count": fail_count})

    status = status_from_issues(issues)
    return {
        "status": status,
        "root": str(root),
        "chapter_count": len(chapters),
        "chapters": chapters,
        "issues": issues,
        "settings": {
            "early_dialogue_limit": early_limit,
            "visible_event_window": window_size,
            "emotion_label_limit": emotion_limit,
        },
    }


def to_markdown(report: dict) -> str:
    issue_rows = [
        [idx + 1, item["severity"], item["type"], item["location"], item["message"], item.get("evidence", "")]
        for idx, item in enumerate(report["issues"])
    ]
    if not issue_rows:
        issue_rows = [["-", "-", "-", "-", "No scene-density issues found.", ""]]

    chapter_rows = [[item["chapter_id"], item["filename"], item["fail_count"]] for item in report["chapters"]]
    if not chapter_rows:
        chapter_rows = [["-", "No chapter files found.", 0]]

    return "\n\n".join(
        [
            "# Scene Density Report",
            f"- Status: {report['status']}",
            f"- Chapter count: {report['chapter_count']}",
            "## Settings",
            markdown_table(
                ["Early Dialogue Limit", "Visible Event Window", "Emotion Label Limit"],
                [[
                    report["settings"]["early_dialogue_limit"],
                    report["settings"]["visible_event_window"],
                    report["settings"]["emotion_label_limit"],
                ]],
            ),
            "## Chapter Scores",
            markdown_table(["No.", "Filename", "Failed Checks"], chapter_rows),
            "## Issues",
            markdown_table(["#", "Severity", "Type", "Location", "Message", "Evidence"], issue_rows),
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Novel project root.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--early-dialogue-limit", type=int, default=500, help="Compact character window for early dialogue check.")
    parser.add_argument("--visible-event-window", type=int, default=1000, help="Compact character window for visible-event density check.")
    parser.add_argument("--emotion-label-limit", type=int, default=6, help="Warn when abstract emotion labels exceed this count per chapter.")
    parser.add_argument("--write-report", nargs="?", const="reports/scene_density_report.md", help="Write Markdown report to path.")
    args = parser.parse_args()

    root = root_path(args.root)
    report = build_report(root, args.early_dialogue_limit, args.visible_event_window, args.emotion_label_limit)
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
