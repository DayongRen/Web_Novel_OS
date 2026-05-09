"""
check_continuity.py — 连续性快速检查工具
解析 project_repo/canon/ 和最近章节，报告潜在矛盾。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


def load_canon(project_root: Path) -> dict:
    canon = {}
    canon_dir = project_root / "project_repo/canon"
    for f in canon_dir.glob("*.md"):
        canon[f.stem] = f.read_text(encoding="utf-8")
    for f in canon_dir.glob("*.yaml"):
        with open(f, encoding="utf-8") as fh:
            canon[f.stem] = yaml.safe_load(fh) or {}
    return canon


def load_chapters(project_root: Path, last_n: int = 10) -> list[dict]:
    manuscript = project_root / "project_repo/manuscript"
    chapters = []
    if not manuscript.exists():
        return chapters
    for vol_dir in sorted(manuscript.iterdir()):
        if vol_dir.is_dir():
            for ch_file in sorted(vol_dir.glob("ch*.md")):
                num = int(re.search(r"ch(\d+)", ch_file.stem).group(1))
                chapters.append({"num": num, "path": ch_file, "content": ch_file.read_text(encoding="utf-8")})
    return sorted(chapters, key=lambda x: x["num"])[-last_n:]


def check_character_names(canon: dict, chapters: list[dict]) -> list[str]:
    issues = []
    char_bible = canon.get("Character_Bible", "")
    defined_names = set(re.findall(r"##\s+(.+)", char_bible))
    for ch in chapters:
        content = ch["content"]
        for name in defined_names:
            if name and len(name) > 1 and name in content:
                pass
    return issues


def check_timeline_markers(chapters: list[dict]) -> list[str]:
    issues = []
    time_pattern = re.compile(r"(第[一二三四五六七八九十百千\d]+天|[次日|翌日|当天|同日])")
    last_marker = None
    for ch in chapters:
        markers = time_pattern.findall(ch["content"])
        if markers:
            last_marker = markers[-1]
    return issues


def run_continuity_check(project_root: Path, last_n: int = 10) -> str:
    canon = load_canon(project_root)
    chapters = load_chapters(project_root, last_n)

    report_lines = [f"# 连续性快速检查报告\n", f"检查最近 {len(chapters)} 章\n"]

    if not chapters:
        report_lines.append("⚠️ 未找到任何章节文件。")
        return "\n".join(report_lines)

    report_lines.append(f"## 章节覆盖范围\n")
    report_lines.append(f"第 {chapters[0]['num']} 章 — 第 {chapters[-1]['num']} 章\n")

    report_lines.append(f"## Canon 文件状态\n")
    for key in ["World_Bible", "Character_Bible", "Power_System", "Faction_Map", "Timeline"]:
        status = "✅ 存在" if key in canon else "❌ 缺失"
        report_lines.append(f"- {key}: {status}")

    report_lines.append(f"\n## 章节字数统计\n")
    for ch in chapters:
        wc = len(ch["content"])
        flag = "⚠️ 偏短" if wc < 1000 else ("⚠️ 超长" if wc > 5000 else "✅")
        report_lines.append(f"- 第{ch['num']}章: {wc}字 {flag}")

    promise_map_path = project_root / "project_repo/continuity/Promise_Payoff_Map.yaml"
    if promise_map_path.exists():
        with open(promise_map_path, encoding="utf-8") as f:
            pm = yaml.safe_load(f) or {}
        promises = pm.get("promises", [])
        open_promises = [p for p in promises if p.get("status") == "open"]
        report_lines.append(f"\n## 承诺状态\n")
        report_lines.append(f"- 开放承诺: {len(open_promises)} 条")
        if len(open_promises) > 10:
            report_lines.append(f"  ⚠️ 开放承诺超过10条，存在管理风险")
        for p in open_promises:
            if p.get("urgency") == "high":
                report_lines.append(f"  🔴 HIGH: {p.get('id')} — {p.get('promise', '')[:50]}")

    report_lines.append(f"\n---\n检查完成。")
    return "\n".join(report_lines)


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print(run_continuity_check(root))
