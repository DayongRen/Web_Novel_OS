"""
tools/quality_gate.py — 质量门禁

每批章节写完后执行，严重失败时阻断流程并生成 Rewrite_Request.md。
门禁配置来自 novel_config.yaml 的 quality_gates 节。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


ROOT = Path(__file__).parent.parent


@dataclass
class GateResult:
    name: str
    passed: bool
    severity: str = "warn"
    message: str = ""
    detail: str = ""


@dataclass
class QualityGateReport:
    results: list[GateResult] = field(default_factory=list)
    blocked: bool = False
    block_reasons: list[str] = field(default_factory=list)

    def add(self, result: GateResult) -> None:
        self.results.append(result)
        if not result.passed and result.severity == "block":
            self.blocked = True
            self.block_reasons.append(f"{result.name}: {result.message}")

    def to_markdown(self) -> str:
        lines = ["# 质量门禁报告\n"]
        if self.blocked:
            lines.append(f"## 🚨 流程已阻断\n\n{''.join(f'- {r}' + chr(10) for r in self.block_reasons)}")
        else:
            lines.append("## ✅ 通过所有门禁\n")

        lines.append("## 检查结果\n")
        for r in self.results:
            icon = "✅" if r.passed else ("🚨" if r.severity == "block" else "⚠️")
            lines.append(f"### {icon} {r.name}")
            lines.append(f"{r.message}")
            if r.detail:
                lines.append(f"\n{r.detail}")
            lines.append("")
        return "\n".join(lines)


def gate_continuity(project_root: Path, run_dir: Path, config: dict) -> GateResult:
    from tools.check_continuity import run_continuity_check
    report = run_continuity_check(project_root)
    fail_markers = ["❌", "CRITICAL"]
    passed = not any(m in report for m in fail_markers)
    block_on_fail = config.get("quality_gates", {}).get("stop_on", {}).get("continuity_fail", False)
    return GateResult(
        name="连续性检查",
        passed=passed,
        severity="block" if (not passed and block_on_fail) else "warn",
        message="通过" if passed else "发现连续性问题",
        detail=report if not passed else "",
    )


def gate_character_consistency(project_root: Path, run_dir: Path, config: dict) -> GateResult:
    from tools.check_character_consistency import run_character_check
    report = run_character_check(project_root)
    fail_markers = ["❌ FAIL"]
    passed = not any(m in report for m in fail_markers)
    block_on_fail = config.get("quality_gates", {}).get("stop_on", {}).get("character_consistency_fail", False)
    return GateResult(
        name="人物一致性",
        passed=passed,
        severity="block" if (not passed and block_on_fail) else "warn",
        message="通过" if passed else "发现人物一致性问题",
        detail="" if passed else report[:500],
    )


def gate_promise_payoff(project_root: Path, current_chapter: int, config: dict) -> GateResult:
    from tools.check_promise_payoff import run_promise_check
    from schemas.promise_schema import PromisePayoffMap

    pm_path = project_root / "project_repo/continuity/Promise_Payoff_Map.yaml"
    pm = PromisePayoffMap.load(pm_path)
    health = pm.health_check(current_chapter)

    gates_cfg = config.get("quality_gates", {}).get("stop_on", {})
    max_open = config.get("quality_gates", {}).get("max_open_promises", 12)
    max_high = config.get("quality_gates", {}).get("max_high_urgency_open", 3)

    issues = []
    if health["overdue"] > 0 and gates_cfg.get("overdue_major_promise", False):
        issues.append(f"🚨 {health['overdue']} 条承诺已逾期: {', '.join(health['overdue_ids'])}")
    if health["open"] > max_open:
        issues.append(f"⚠️ 开放承诺 {health['open']} 条（上限 {max_open}）")
    if health["high_urgency"] > max_high:
        issues.append(f"⚠️ 高优先级开放承诺 {health['high_urgency']} 条（上限 {max_high}）")

    passed = len(issues) == 0
    block = not passed and health["overdue"] > 0 and gates_cfg.get("overdue_major_promise", False)
    return GateResult(
        name="承诺-回报健康度",
        passed=passed,
        severity="block" if block else "warn",
        message="通过" if passed else f"发现 {len(issues)} 个问题",
        detail="\n".join(issues) if issues else "",
    )


def gate_pacing(project_root: Path, config: dict) -> GateResult:
    from tools.check_pacing import run_pacing_check
    report = run_pacing_check(project_root, config)
    water_chapter_ratio = config.get("quality_gates", {}).get("stop_on", {}).get("water_chapter_ratio_over", 0.25)
    water_count = report.count("💧水")
    chapter_count = max(report.count("| 第"), 1)
    ratio = water_count / chapter_count
    passed = ratio <= water_chapter_ratio
    block_on_fail = config.get("quality_gates", {}).get("stop_on", {}).get("water_chapter_ratio_over") is not None
    return GateResult(
        name="节奏/水章检查",
        passed=passed,
        severity="warn",
        message="通过" if passed else f"水章比例 {ratio:.0%}（上限 {water_chapter_ratio:.0%}）",
        detail=report if not passed else "",
    )


def gate_chapter_hooks(project_root: Path, config: dict) -> GateResult:
    from tools.check_chapter_hooks import run_hook_check
    report = run_hook_check(project_root)
    fail_count = report.count("❌D") + report.count("💀F")
    total = max(report.count("| 第"), 1)
    fail_ratio = fail_count / total
    block_on_fail = config.get("quality_gates", {}).get("stop_on", {}).get("missing_chapter_hook", False)
    passed = fail_ratio < 0.3
    return GateResult(
        name="章节钩子质量",
        passed=passed,
        severity="block" if (not passed and block_on_fail) else "warn",
        message="通过" if passed else f"D/F 级钩子占比 {fail_ratio:.0%}",
        detail="" if passed else report[:500],
    )


def run_quality_gate(
    project_root: Path,
    run_dir: Path,
    current_chapter: int = 0,
    config: dict = None,
) -> QualityGateReport:
    if config is None:
        cfg_path = project_root / "novel_config.yaml"
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

    report = QualityGateReport()
    report.add(gate_continuity(project_root, run_dir, config))
    report.add(gate_character_consistency(project_root, run_dir, config))
    report.add(gate_promise_payoff(project_root, current_chapter, config))
    report.add(gate_pacing(project_root, config))
    report.add(gate_chapter_hooks(project_root, config))

    md = report.to_markdown()
    out = run_dir / "Quality_Gate_Report.md"
    out.write_text(md, encoding="utf-8")

    if report.blocked:
        rewrite_req = run_dir / "Rewrite_Request.md"
        req_content = "# Rewrite Request\n\n质量门禁阻断，以下章节需要修改后才能继续：\n\n"
        req_content += "\n".join(f"- {r}" for r in report.block_reasons)
        req_content += "\n\n## 修复后操作\n\n```bash\npython runner.py run --stage chapters --batch 5\n```\n"
        rewrite_req.write_text(req_content, encoding="utf-8")

    return report


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    ch = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    rd = root / "runs" / "GATE_TEST"
    rd.mkdir(parents=True, exist_ok=True)
    rep = run_quality_gate(root, rd, ch)
    print(rep.to_markdown())
    if rep.blocked:
        print("\n🚨 流程已阻断！")
        sys.exit(1)
