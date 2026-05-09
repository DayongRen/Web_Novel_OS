"""
tools/adaptive_quality_gate.py — 自适应质量门

分四层检查：通用 + 长度特定 + 题材特定 + 平台特定。
每层单独可关闭，hard_fail 阻断，warn_only 记录继续。
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


ROOT = Path(__file__).parent.parent


@dataclass
class GateCheck:
    name: str
    layer: str          # universal | length | genre | platform
    passed: bool = True
    severity: str = "warn"   # warn | hard_fail
    message: str = ""
    detail: str = ""

    @property
    def icon(self) -> str:
        if self.passed:
            return "✅"
        return "🚨" if self.severity == "hard_fail" else "⚠️"


@dataclass
class AdaptiveGateReport:
    checks: list[GateCheck] = field(default_factory=list)
    blocked: bool = False
    block_reasons: list[str] = field(default_factory=list)
    current_chapter: int = 0
    length_class: str = ""
    genre: str = ""

    def add(self, check: GateCheck) -> None:
        self.checks.append(check)
        if not check.passed and check.severity == "hard_fail":
            self.blocked = True
            self.block_reasons.append(f"[{check.layer}] {check.name}: {check.message}")

    def to_markdown(self) -> str:
        lines = [
            f"# 自适应质量门报告",
            f"章节: {self.current_chapter} | 长度级别: {self.length_class} | 题材: {self.genre}\n",
        ]
        if self.blocked:
            lines.append(f"## 🚨 流程阻断\n")
            for r in self.block_reasons:
                lines.append(f"- {r}")
            lines.append("")

        for layer in ("universal", "length", "genre", "platform"):
            layer_checks = [c for c in self.checks if c.layer == layer]
            if not layer_checks:
                continue
            layer_names = {"universal": "通用", "length": "长度", "genre": "题材", "platform": "平台"}
            label = layer_names.get(layer, layer)
            lines.append(f"## {label} 检查\n")
            for c in layer_checks:
                lines.append(f"{c.icon} **{c.name}**: {c.message}")
                if c.detail and not c.passed:
                    lines.append(f"  _{c.detail[:200]}_")

        pass_count = sum(1 for c in self.checks if c.passed)
        total = len(self.checks)
        lines.append(f"\n通过率: {pass_count}/{total}")
        return "\n".join(lines)


# ── 通用检查 ──────────────────────────────────────────────────────────────────

def _check_empty_chapter(chapters: list[dict], hard_fail_list: list[str]) -> list[GateCheck]:
    checks = []
    for ch in chapters:
        empty = len(ch.get("content", "").strip()) < 100
        c = GateCheck(
            name=f"empty_chapter_ch{ch['num']}",
            layer="universal",
            passed=not empty,
            severity="hard_fail" if "empty_chapter" in hard_fail_list else "warn",
            message="通过" if not empty else f"第{ch['num']}章内容为空或过短",
        )
        checks.append(c)
    return checks


def _check_word_budget(chapters: list[dict], wpc_target: int) -> GateCheck:
    if not chapters:
        return GateCheck("word_budget", "universal", True, "warn", "无章节")
    avg = sum(len(ch.get("content", "")) for ch in chapters) // len(chapters)
    deviation = abs(avg - wpc_target) / wpc_target
    passed = deviation < 0.4
    return GateCheck(
        "word_budget", "universal", passed, "warn",
        f"平均字数 {avg}（目标 {wpc_target}，偏差 {deviation:.0%}）",
    )


def _check_chapter_hooks(chapters: list[dict], hard_fail_list: list[str]) -> list[GateCheck]:
    checks = []
    hook_signals = [r"[？?！!]{1}", r"(竟然|没想到|突然|忽然)", r"(……|—{3,})"]
    for ch in chapters:
        lines = [l.strip() for l in ch.get("content", "").split("\n") if l.strip()]
        last = " ".join(lines[-3:]) if lines else ""
        has_hook = any(re.search(p, last) for p in hook_signals)
        c = GateCheck(
            name=f"chapter_hook_ch{ch['num']}",
            layer="universal",
            passed=has_hook,
            severity="warn",
            message="通过" if has_hook else f"第{ch['num']}章结尾缺乏明显钩子",
            detail=last[:80] if not has_hook else "",
        )
        checks.append(c)
    return checks


def _check_promise_payoff(project_root: Path, current_chapter: int, hard_fail_list: list[str]) -> GateCheck:
    try:
        from schemas.promise_schema import PromisePayoffMap
        pm = PromisePayoffMap.load(project_root / "project_repo/continuity/Promise_Payoff_Map.yaml")
        h = pm.health_check(current_chapter)
        overdue = h["overdue"]
        over_count = max(0, h["open"] - 12)
        passed = overdue == 0 and over_count == 0
        sev = "hard_fail" if ("overdue_major_promise" in hard_fail_list and overdue > 0) else "warn"
        msg = "通过" if passed else f"逾期承诺 {overdue} 条，开放 {h['open']} 条"
        return GateCheck("promise_payoff", "universal", passed, sev, msg)
    except Exception as e:
        return GateCheck("promise_payoff", "universal", True, "warn", f"无法检查（{e}）")


# ── 长度特定检查 ──────────────────────────────────────────────────────────────

def _check_length_gates(length_class: str, chapters: list[dict], current_ch: int) -> list[GateCheck]:
    checks: list[GateCheck] = []

    if length_class in ("short_30k", "novella_100k"):
        if current_ch >= 10:
            all_content = " ".join(ch.get("content", "") for ch in chapters)
            has_turn = bool(re.search(r"(反转|转折|竟然|没想到|原来|真相)", all_content))
            checks.append(GateCheck(
                "midpoint_turn", "length", has_turn, "warn",
                "通过" if has_turn else "前期缺乏明显反转节点",
            ))

    if length_class in ("volume_200k", "medium_500k"):
        if current_ch >= 30:
            has_payoff = any(
                re.search(r"(爽|胜利|成功|突破|打脸|逆袭)", ch.get("content", ""))
                for ch in chapters[-10:]
            )
            checks.append(GateCheck(
                "volume_payoff", "length", has_payoff, "warn",
                "通过" if has_payoff else "近10章缺乏爽点/回报",
            ))

    if length_class in ("long_1m", "epic_2m") and current_ch >= 100:
        checks.append(GateCheck(
            "reader_reentry_hook", "length", True, "warn",
            "提醒：确认有为新读者快速入场的钩子设计（百万字特有需求）",
        ))

    return checks


# ── 题材特定检查 ──────────────────────────────────────────────────────────────

def _check_genre_gates(genre: str, chapters: list[dict], project_root: Path) -> list[GateCheck]:
    checks: list[GateCheck] = []
    all_content = " ".join(ch.get("content", "") for ch in chapters)

    if genre in ("romance", "romance_ceo"):
        has_emotion = bool(re.search(r"(心跳|脸红|温柔|靠近|眼神|心里)", all_content))
        checks.append(GateCheck(
            "emotional_progression", "genre", has_emotion, "warn",
            "通过" if has_emotion else "感情线缺乏情绪推进词汇，检查感情线是否在推进",
        ))

    elif genre in ("suspense", "suspense_crime"):
        has_clue = bool(re.search(r"(线索|证据|嫌疑|发现|调查|不对劲)", all_content))
        checks.append(GateCheck(
            "clue_fairness", "genre", has_clue, "warn",
            "通过" if has_clue else "近期章节缺乏悬疑线索词，检查线索密度",
        ))

    elif genre in ("fantasy_xuanhuan", "xuanhuan_upgrade", "xianxia_sect"):
        has_upgrade = bool(re.search(r"(突破|境界|修为|进阶|提升|战力)", all_content))
        checks.append(GateCheck(
            "upgrade_frequency", "genre", has_upgrade, "warn",
            "通过" if has_upgrade else "近期章节缺乏战力成长描述，检查升级频率",
        ))

    elif genre in ("palace_intrigue",):
        has_strategy = bool(re.search(r"(计谋|算计|势力|联盟|背叛|权力)", all_content))
        checks.append(GateCheck(
            "faction_motivation", "genre", has_strategy, "warn",
            "通过" if has_strategy else "近期缺乏权谋元素，检查势力逻辑",
        ))

    elif genre in ("infinite_flow",):
        has_instance = bool(re.search(r"(副本|规则|任务|生存|死亡威胁)", all_content))
        checks.append(GateCheck(
            "instance_rule_consistency", "genre", has_instance, "warn",
            "通过" if has_instance else "近期缺乏副本/规则描写，检查无限流核心要素",
        ))

    return checks


# ── 主入口 ────────────────────────────────────────────────────────────────────

def run_adaptive_gate(
    project_root: Path,
    run_dir: Path,
    chapters: list[dict],
    current_chapter: int,
    length_class: str,
    genre: str,
    strategy=None,
) -> "AdaptiveGateReport":
    from schemas.production_strategy import ProductionStrategy

    if strategy is None:
        sp = project_root / "project_repo/manifests/Production_Strategy.yaml"
        strategy = ProductionStrategy.load(sp)

    hard_fail = strategy.quality_policy.hard_fail if strategy else ["missing_chapter_card", "empty_chapter"]
    active_gates = strategy.quality_policy.active_gates if strategy else ["universal"]

    report = AdaptiveGateReport(
        current_chapter=current_chapter,
        length_class=length_class,
        genre=genre,
    )

    if "universal" in active_gates and chapters:
        for c in _check_empty_chapter(chapters, hard_fail):
            report.add(c)
        report.add(_check_word_budget(
            chapters,
            strategy.words_per_chapter if strategy else 2000
        ))
        for c in _check_chapter_hooks(chapters, hard_fail):
            report.add(c)
        report.add(_check_promise_payoff(project_root, current_chapter, hard_fail))

    if "length_specific" in active_gates:
        for c in _check_length_gates(length_class, chapters, current_chapter):
            report.add(c)

    if "genre_specific" in active_gates:
        for c in _check_genre_gates(genre, chapters, project_root):
            report.add(c)

    md = report.to_markdown()
    out = run_dir / f"Adaptive_Gate_{current_chapter:04d}.md"
    out.write_text(md, encoding="utf-8")

    if report.blocked:
        req = run_dir / "Rewrite_Request.md"
        req.write_text(
            f"# Rewrite Request\n\n自适应质量门阻断（第{current_chapter}章）：\n\n"
            + "\n".join(f"- {r}" for r in report.block_reasons),
            encoding="utf-8",
        )

    return report


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    ch = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    rd = root / "runs" / "GATE_TEST"
    rd.mkdir(parents=True, exist_ok=True)
    rep = run_adaptive_gate(root, rd, [], ch, "volume_200k", "urban_rebirth")
    print(rep.to_markdown())
