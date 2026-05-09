"""
check_pacing.py — 节奏快速检查工具
基于配置文件检查章节字数、钩子密度和爽点间隔。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


HOOK_PATTERNS = [
    r"[？?！!。]{1,2}$",
    r"(突然|忽然|却|竟然|没想到)",
    r"(……|—{2,})",
]

PAYOFF_PATTERNS = [
    r"(打脸|反转|揭露|真相|逆袭|胜利|成功)",
    r"(突破|晋级|升级|境界)",
    r"(认出|认清|发现秘密)",
]

FILLER_PATTERNS = [
    r"(缓缓|慢慢地|就这样|话说回来|闲话不提)",
    r"(思绪|回忆|前世|想起了)",
]


def analyze_chapter(content: str) -> dict:
    word_count = len(content)
    paragraphs = [p.strip() for p in content.split("\n") if p.strip()]

    last_para = paragraphs[-1] if paragraphs else ""
    hook_score = 0
    for pat in HOOK_PATTERNS:
        if re.search(pat, last_para):
            hook_score += 1

    payoff_count = sum(
        len(re.findall(pat, content)) for pat in PAYOFF_PATTERNS
    )

    filler_count = sum(
        len(re.findall(pat, content)) for pat in FILLER_PATTERNS
    )

    dialogue_count = content.count("“") + content.count("「")
    dialogue_ratio = dialogue_count * 20 / max(word_count, 1)

    return {
        "word_count": word_count,
        "hook_score": hook_score,
        "payoff_count": payoff_count,
        "filler_count": filler_count,
        "dialogue_ratio": round(dialogue_ratio, 2),
        "last_line": last_para[:80],
    }


def run_pacing_check(project_root: Path, config: dict = None, last_n: int = 20) -> str:
    if config is None:
        config_path = project_root / "novel_config.yaml"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

    pacing = config.get("pacing", {})
    small_interval = pacing.get("small_payoff_every_chapters", 2)
    target_wc = config.get("project", {}).get("words_per_chapter", 2000)

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
        return "# 节奏检查\n\n⚠️ 未找到章节文件。"

    report = [
        "# 节奏快速检查报告\n",
        f"检查最近 {len(chapters)} 章 | 目标字数/章: {target_wc}\n",
        "## 逐章分析\n",
        "| 章节 | 字数 | 钩子 | 爽点 | 水文标记 | 末尾预览 |",
        "|------|------|------|------|---------|---------|",
    ]

    water_chapters = []
    for ch in chapters:
        stats = analyze_chapter(ch["content"])
        wc_flag = "✅" if abs(stats["word_count"] - target_wc) / target_wc < 0.3 else "⚠️"
        hook_flag = "🎣" if stats["hook_score"] > 0 else "❌"
        payoff_flag = "🎯" * min(stats["payoff_count"], 3) or "·"
        is_water = stats["word_count"] < target_wc * 0.7 and stats["payoff_count"] == 0 and stats["hook_score"] == 0
        water_flag = "💧水" if is_water else ""
        if is_water:
            water_chapters.append(ch["num"])

        report.append(
            f"| 第{ch['num']}章 | {stats['word_count']}{wc_flag} | {hook_flag} | "
            f"{payoff_flag} | {water_flag} | {stats['last_line'][:30]}... |"
        )

    if water_chapters:
        report.append(f"\n## ⚠️ 疑似水章\n第 {', '.join(map(str, water_chapters))} 章需要人工复查。")

    payoff_chapters = [ch["num"] for ch in chapters if analyze_chapter(ch["content"])["payoff_count"] > 0]
    if payoff_chapters:
        intervals = [payoff_chapters[i+1] - payoff_chapters[i] for i in range(len(payoff_chapters)-1)]
        if intervals:
            max_interval = max(intervals)
            if max_interval > small_interval * 2:
                report.append(f"\n## ⚠️ 爽点间隔过长\n最长连续 {max_interval} 章无爽点（建议上限: {small_interval * 2} 章）。")

    report.append("\n---\n检查完成。")
    return "\n".join(report)


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print(run_pacing_check(root))
