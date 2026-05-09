"""
check_character_consistency.py — 人物一致性快速检查工具
基于 Character_Bible 和章节内容，检测简单的一致性问题。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


def load_character_bible(project_root: Path) -> dict:
    path = project_root / "project_repo/canon/Character_Bible.md"
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")
    characters = {}
    current_char = None
    for line in content.split("\n"):
        if line.startswith("## "):
            current_char = line[3:].strip()
            characters[current_char] = {"raw": ""}
        elif current_char:
            characters[current_char]["raw"] += line + "\n"
    return characters


def load_arc_tracker(project_root: Path) -> dict:
    path = project_root / "project_repo/continuity/Character_Arc_Tracker.yaml"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def check_name_frequency(characters: dict, chapters: list[dict]) -> list[str]:
    issues = []
    for ch in chapters:
        content = ch["content"]
        for name in characters:
            if name and len(name) >= 2:
                count = content.count(name)
                if count > 30:
                    issues.append(f"第{ch['num']}章：{name} 出现{count}次，可能过于密集")
    return issues


def check_missing_characters(characters: dict, chapters: list[dict]) -> list[str]:
    issues = []
    all_text = " ".join(ch["content"] for ch in chapters)
    for name in characters:
        if name and len(name) >= 2:
            if name not in all_text:
                pass
    return issues


def run_character_check(project_root: Path, chapter_range: tuple = None) -> str:
    characters = load_character_bible(project_root)
    arc_tracker = load_arc_tracker(project_root)

    manuscript = project_root / "project_repo/manuscript"
    chapters = []
    if manuscript.exists():
        for vol_dir in sorted(manuscript.iterdir()):
            if vol_dir.is_dir():
                for ch_file in sorted(vol_dir.glob("ch*.md")):
                    num_match = re.search(r"ch(\d+)", ch_file.stem)
                    if num_match:
                        num = int(num_match.group(1))
                        if chapter_range is None or (chapter_range[0] <= num <= chapter_range[1]):
                            chapters.append({
                                "num": num,
                                "content": ch_file.read_text(encoding="utf-8")
                            })

    report_lines = [
        "# 人物一致性检查报告\n",
        f"检查章节数：{len(chapters)}\n",
        f"已建档人物数：{len(characters)}\n",
    ]

    report_lines.append("## 已建档人物列表\n")
    for name in characters:
        tracker_info = ""
        if arc_tracker:
            chars_list = arc_tracker.get("characters", [])
            for c in chars_list:
                if c.get("name") == name:
                    tracker_info = f" | 弧线阶段: {c.get('arc_stage', 'unknown')}"
        report_lines.append(f"- {name}{tracker_info}")

    if chapters:
        name_issues = check_name_frequency(characters, chapters)
        if name_issues:
            report_lines.append("\n## 频率异常警告\n")
            for issue in name_issues:
                report_lines.append(f"- ⚠️ {issue}")

    report_lines.append("\n## 弧线追踪状态\n")
    if arc_tracker:
        chars_list = arc_tracker.get("characters", [])
        for c in chars_list:
            pending = c.get("pending_arc_beats", [])
            if pending:
                report_lines.append(f"- **{c.get('name')}**: 待完成弧线节点 {len(pending)} 个")
                for beat in pending[:3]:
                    report_lines.append(f"  - {beat}")
    else:
        report_lines.append("⚠️ Character_Arc_Tracker.yaml 不存在，无法检查弧线状态")

    report_lines.append("\n---\n检查完成。")
    return "\n".join(report_lines)


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print(run_character_check(root))
