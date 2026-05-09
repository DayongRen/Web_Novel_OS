"""
check_word_budget.py — 字数预算检查工具
追踪已写字数、剩余字数、分卷进度。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


def run_word_budget_check(project_root: Path) -> str:
    config_path = project_root / "novel_config.yaml"
    config = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    target_total = config.get("project", {}).get("target_word_count", 300000)
    target_chapters = config.get("project", {}).get("target_chapter_count", 150)
    target_per_chapter = config.get("project", {}).get("words_per_chapter", 2000)
    volume_size = config.get("structure", {}).get("volume_size_chapters", 80)

    manuscript = project_root / "project_repo/manuscript"
    volume_stats = {}
    total_words = 0
    total_chapters = 0

    if manuscript.exists():
        for vol_dir in sorted(manuscript.iterdir()):
            if vol_dir.is_dir() and vol_dir.name.startswith("volume_"):
                vol_name = vol_dir.name
                vol_words = 0
                vol_chapters = 0
                for ch_file in vol_dir.glob("ch*.md"):
                    content = ch_file.read_text(encoding="utf-8")
                    wc = len(content)
                    vol_words += wc
                    vol_chapters += 1
                volume_stats[vol_name] = {"words": vol_words, "chapters": vol_chapters}
                total_words += vol_words
                total_chapters += vol_chapters

    completion_pct = total_words / target_total * 100 if target_total > 0 else 0
    chapter_pct = total_chapters / target_chapters * 100 if target_chapters > 0 else 0
    remaining_words = target_total - total_words
    remaining_chapters = target_chapters - total_chapters

    report = [
        "# 字数预算报告\n",
        f"## 总体进度\n",
        f"| 指标 | 已完成 | 目标 | 进度 |",
        f"|------|-------|------|------|",
        f"| 总字数 | {total_words:,} | {target_total:,} | {completion_pct:.1f}% |",
        f"| 总章数 | {total_chapters} | {target_chapters} | {chapter_pct:.1f}% |\n",
    ]

    progress_bar_len = 30
    filled = int(completion_pct / 100 * progress_bar_len)
    bar = "█" * filled + "░" * (progress_bar_len - filled)
    report.append(f"进度条: [{bar}] {completion_pct:.1f}%\n")

    report.append(f"## 剩余工作量\n")
    report.append(f"- 剩余字数: **{remaining_words:,}** 字")
    report.append(f"- 剩余章数: **{remaining_chapters}** 章")
    if remaining_chapters > 0:
        est_days_5ch = remaining_chapters / 5
        report.append(f"- 按每天5章速度: 约 **{est_days_5ch:.1f}** 天完成\n")

    if volume_stats:
        report.append(f"## 分卷统计\n")
        report.append(f"| 卷 | 章数 | 字数 | 平均字/章 |")
        report.append(f"|-----|------|------|---------|")
        for vol_name, stats in sorted(volume_stats.items()):
            avg = stats["words"] // max(stats["chapters"], 1)
            vol_label = vol_name.replace("volume_", "第") + "卷"
            report.append(f"| {vol_label} | {stats['chapters']} | {stats['words']:,} | {avg} |")

    if total_chapters > 0:
        actual_avg = total_words // total_chapters
        deviation = (actual_avg - target_per_chapter) / target_per_chapter * 100
        report.append(f"\n## 字数密度\n")
        report.append(f"- 目标字数/章: {target_per_chapter}")
        report.append(f"- 实际平均: {actual_avg}")
        flag = "✅" if abs(deviation) < 20 else "⚠️"
        report.append(f"- 偏差: {deviation:+.1f}% {flag}")
        if deviation < -20:
            report.append("  → 章节偏短，注意内容充实度")
        elif deviation > 20:
            report.append("  → 章节偏长，注意节奏和水分")

    report.append("\n---\n检查完成。")
    return "\n".join(report)


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print(run_word_budget_check(root))
