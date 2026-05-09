"""
check_promise_payoff.py — 承诺-回报状态检查工具
解析 Promise_Payoff_Map.yaml，输出健康度报告。
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def parse_payoff_window(window_str: str) -> tuple[int, int]:
    """解析 'chapters 20-40' 格式，返回 (start, end)。"""
    import re
    m = re.search(r"(\d+)[^\d]+(\d+)", str(window_str))
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+)", str(window_str))
    if m:
        v = int(m.group(1))
        return v, v + 10
    return 0, 999


def run_promise_check(project_root: Path, current_chapter: int = 0) -> str:
    path = project_root / "project_repo/continuity/Promise_Payoff_Map.yaml"
    if not path.exists():
        return "# 承诺-回报检查\n\n⚠️ Promise_Payoff_Map.yaml 不存在。请先运行 outline 阶段。"

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    promises = data.get("promises", [])
    if not promises:
        return "# 承诺-回报检查\n\n当前无已登记的承诺。"

    open_p = [p for p in promises if p.get("status") == "open"]
    planned_p = [p for p in promises if p.get("status") == "planned"]
    partial_p = [p for p in promises if p.get("status") == "partial"]
    closed_p = [p for p in promises if p.get("status") == "closed"]
    abandoned_p = [p for p in promises if p.get("status") == "abandoned"]

    overdue = []
    if current_chapter > 0:
        for p in open_p + planned_p:
            _, end = parse_payoff_window(p.get("expected_payoff_window", "999"))
            if current_chapter > end:
                overdue.append(p)

    high_urgency = [p for p in open_p if p.get("urgency") == "high"]

    report = [
        "# 承诺-回报健康度报告\n",
        f"当前章节：第{current_chapter}章\n",
        f"## 状态概览\n",
        f"| 状态 | 数量 |",
        f"|------|------|",
        f"| 🔴 开放中 | {len(open_p)} |",
        f"| 🟡 已规划 | {len(planned_p)} |",
        f"| 🟠 部分回收 | {len(partial_p)} |",
        f"| ✅ 已关闭 | {len(closed_p)} |",
        f"| ⚫ 已放弃 | {len(abandoned_p)} |",
        f"| **总计** | **{len(promises)}** |\n",
    ]

    if overdue:
        report.append("## 🚨 逾期承诺（必须立即处理）\n")
        for p in overdue:
            report.append(f"- **{p.get('id')}** [{p.get('type')}]: {p.get('promise', '')}")
            report.append(f"  预计回收窗口: {p.get('expected_payoff_window')}，当前章节: {current_chapter}")
            report.append(f"  计划: {p.get('payoff_plan', '无')}\n")

    if high_urgency:
        report.append("## 🔴 高优先级开放承诺\n")
        for p in high_urgency:
            report.append(f"- **{p.get('id')}** ({p.get('chapter_opened')}章开启): {p.get('promise', '')}")
            report.append(f"  回收窗口: {p.get('expected_payoff_window')}")
            report.append(f"  计划: {p.get('payoff_plan', '待定')}\n")

    if len(open_p) > 10:
        report.append(f"## ⚠️ 承诺过多警告\n当前开放承诺 {len(open_p)} 条，超过推荐上限(10)。建议优先回收以下承诺：\n")
        for p in sorted(open_p, key=lambda x: x.get("urgency", "low") == "high", reverse=True)[:5]:
            report.append(f"- {p.get('id')}: {p.get('promise', '')[:60]}")

    report.append("\n## 所有开放承诺\n")
    for p in open_p:
        urgency_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(p.get("urgency", "low"), "⚪")
        report.append(f"- {urgency_icon} **{p.get('id')}** [{p.get('type')}] (第{p.get('chapter_opened')}章)")
        report.append(f"  > {p.get('promise', '')}")
        report.append(f"  > 预计回收: {p.get('expected_payoff_window')}\n")

    report.append("\n---\n检查完成。")
    return "\n".join(report)


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    current_ch = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(run_promise_check(root, current_ch))
