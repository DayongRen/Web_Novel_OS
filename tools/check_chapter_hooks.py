"""
check_chapter_hooks.py — 章节钩子质量检查工具
检查每章的结尾是否有足够的前向钩子。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


STRONG_HOOK_SIGNALS = [
    r"[？?！!]{1}$",
    r"(竟然|没想到|居然|突然|忽然)",
    r"(……|—{3,})",
    r"(真相|秘密|身份|来历)",
    r"(不对劲|感觉|预感|察觉)",
]

WEAK_HOOK_SIGNALS = [
    r"(继续|随后|之后|接下来)",
    r"(微微一笑|点了点头|转身离开)",
]


def analyze_chapter_hook(content: str, chapter_num: int) -> dict:
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    if not lines:
        return {"chapter": chapter_num, "score": 0, "grade": "F", "last_lines": [], "issues": ["章节为空"]}

    last_3_lines = lines[-3:] if len(lines) >= 3 else lines
    last_text = " ".join(last_3_lines)

    strong_hits = sum(1 for pat in STRONG_HOOK_SIGNALS if re.search(pat, last_text))
    weak_hits = sum(1 for pat in WEAK_HOOK_SIGNALS if re.search(pat, last_text))

    score = strong_hits * 2 + (1 if weak_hits > 0 else 0)

    if score >= 4:
        grade = "A"
    elif score >= 2:
        grade = "B"
    elif score >= 1:
        grade = "C"
    else:
        grade = "D"

    issues = []
    if strong_hits == 0:
        issues.append("末尾缺少强钩子信号（悬念/反转/揭露）")
    if lines[-1].endswith("。") and strong_hits == 0:
        issues.append("章节以平静句号结束，缺乏张力")

    return {
        "chapter": chapter_num,
        "score": score,
        "grade": grade,
        "last_lines": last_3_lines,
        "issues": issues,
    }


def run_hook_check(project_root: Path, last_n: int = 20) -> str:
    manuscript = project_root / "project_repo/manuscript"
    chapters = []
    if manuscript.exists():
        for vol_dir in sorted(manuscript.iterdir()):
            if vol_dir.is_dir():
                for ch_file in sorted(vol_dir.glob("ch*.md")):
                    m = re.search(r"ch(\d+)", ch_file.stem)
                    if m:
                        chapters.append({
                            "num": int(m.group(1)),
                            "content": ch_file.read_text(encoding="utf-8")
                        })

    chapters = sorted(chapters, key=lambda x: x["num"])[-last_n:]

    if not chapters:
        return "# 钩子检查\n\n⚠️ 未找到章节文件。"

    report = [
        "# 章节钩子质量报告\n",
        f"检查最近 {len(chapters)} 章\n",
        "## 逐章评级\n",
        "| 章节 | 评级 | 末尾内容预览 |",
        "|------|------|------------|",
    ]

    grade_count = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    weak_chapters = []

    for ch in chapters:
        result = analyze_chapter_hook(ch["content"], ch["num"])
        grade_icon = {"A": "🔥", "B": "✅", "C": "⚠️", "D": "❌", "F": "💀"}.get(result["grade"], "?")
        last_preview = result["last_lines"][-1][:40] if result["last_lines"] else "(空)"
        report.append(f"| 第{ch['num']}章 | {grade_icon}{result['grade']} | {last_preview}... |")
        grade_count[result["grade"]] = grade_count.get(result["grade"], 0) + 1
        if result["grade"] in ("C", "D", "F"):
            weak_chapters.append(result)

    report.append(f"\n## 评级分布\n")
    for grade, icon in [("A", "🔥"), ("B", "✅"), ("C", "⚠️"), ("D", "❌")]:
        count = grade_count.get(grade, 0)
        bar = "█" * count
        report.append(f"{icon} {grade}: {count} 章 {bar}")

    if weak_chapters:
        report.append(f"\n## 需要优化的钩子（C/D级）\n")
        for w in weak_chapters:
            report.append(f"### 第{w['chapter']}章 [{w['grade']}级]")
            report.append(f"末尾：{w['last_lines'][-1] if w['last_lines'] else '(空)'}")
            for issue in w["issues"]:
                report.append(f"- 问题：{issue}")
            report.append("")

    total = len(chapters)
    good = grade_count.get("A", 0) + grade_count.get("B", 0)
    report.append(f"\n## 总体评估\n")
    report.append(f"钩子合格率：{good}/{total} ({100*good//max(total,1)}%)")
    if good / max(total, 1) < 0.7:
        report.append("⚠️ 钩子合格率低于70%，需要系统性优化章节结尾。")

    report.append("\n---\n检查完成。")
    return "\n".join(report)


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print(run_hook_check(root))
