"""
Promise-Payoff Validator Agent — 承诺-回报校验器
追踪所有读者期待，确保每个承诺都有回收计划。

核心改动（v2）：
  - LLM 只输出 patch（add/update/close），不再整表覆盖
  - 每次写入前经过 PromisePayoffMap schema 校验和合并
  - 生成 Promise_Payoff_Diff.md 记录每次变更
"""

from pathlib import Path
from typing import List

import yaml

from .base_agent import BaseAgent
from schemas.promise_schema import PromisePatch, PromisePayoffMap


class PromisePayoffValidatorAgent(BaseAgent):

    role = "Promise-Payoff Validator（承诺-回报校验器）"
    stage = "validators"
    system_prompt = """
你是承诺-回报校验器，这是整个系统最重要的质量护栏之一。

你的职责：
1. 识别章节中向读者做出的所有承诺
2. 输出结构化 patch（只允许 add/update/close，不允许整表覆盖）
3. 标记逾期未回收的承诺
4. 确保重要承诺有明确的回收计划

承诺类型枚举（type 字段只能用这些值）：
revenge / romance / upgrade / mystery / identity / treasure / punishment /
relationship_repair / power / truth / business / other

状态枚举（status 字段只能用这些值）：
open / planned / partial / closed / abandoned

紧急度枚举（urgency 字段只能用这些值）：
high / medium / low

expected_payoff_window 格式（必须是 dict）：
  start: <int>   # 预计开始回收章节
  end: <int>     # 预计最晚回收章节

ID 格式：P001, P002, P003...（从已有最大 ID 后续排）

⚠️ 严格要求：只输出 YAML，不要任何其他文字。
"""

    PROMISE_MAP_PATH = "project_repo/continuity/Promise_Payoff_Map.yaml"

    def _load_map(self) -> PromisePayoffMap:
        return PromisePayoffMap.load(self.project_root / self.PROMISE_MAP_PATH)

    def _save_map(self, pm: PromisePayoffMap) -> None:
        pm.save(self.project_root / self.PROMISE_MAP_PATH)

    def scan_new_promises(self, chapter_content: str, chapter_num: int, run_dir: Path) -> str:
        pm = self._load_map()
        context = self._build_base_context(layer="volume")
        existing_summary = self._pm_summary(pm)
        next_id = pm.next_id()

        prompt = f"""
{context}

## 现有承诺摘要
{existing_summary}

## 下一个可用 ID
{next_id}

## 第{chapter_num}章内容
{chapter_content}

## 任务：输出承诺变更 patch

分析本章后，输出以下格式的 YAML patch：

```yaml
add_promises:
  - id: {next_id}         # 只在有新承诺时填写
    chapter_opened: {chapter_num}
    type: <类型>
    promise: "<承诺内容描述>"
    expected_payoff_window:
      start: <章节号>
      end: <章节号>
    status: open
    payoff_plan: "<回收计划>"
    urgency: medium
    notes: ""

update_promises:
  - id: <已有ID>           # 只更新已有承诺的状态/计划
    status: planned         # 可更新字段: status, payoff_plan, urgency, notes, expected_payoff_window
    payoff_plan: "<更新的计划>"

close_promises:
  - id: <已有ID>           # 本章已回收的承诺
    payoff_note: "<回收方式描述>"
```

如果某类没有变更，写空列表 `[]`。
只输出 YAML，不要任何解释文字。
"""
        raw = self.call_llm(prompt)
        diff_log = self._apply_and_save(raw, chapter_num, run_dir, f"Ch{chapter_num:03d}")
        return diff_log

    def _apply_and_save(self, raw_yaml: str, current_chapter: int, run_dir: Path, label: str) -> str:
        yaml_content = raw_yaml.strip()
        for fence in ("```yaml", "```yml", "```"):
            if yaml_content.startswith(fence):
                yaml_content = yaml_content[len(fence):]
        if yaml_content.endswith("```"):
            yaml_content = yaml_content[:-3]
        yaml_content = yaml_content.strip()

        try:
            patch_dict = yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError as e:
            err = f"❌ Promise patch YAML 解析失败: {e}\n原始内容:\n{yaml_content[:500]}"
            (run_dir / f"Promise_Patch_ERROR_{label}.txt").write_text(err, encoding="utf-8")
            return err

        try:
            patch = PromisePatch.from_dict(patch_dict)
        except Exception as e:
            err = f"❌ Promise patch schema 校验失败: {e}"
            (run_dir / f"Promise_Patch_ERROR_{label}.txt").write_text(err, encoding="utf-8")
            return err

        pm = self._load_map()
        change_log = pm.apply_patch(patch, current_chapter)
        self._save_map(pm)

        diff_md = f"# Promise-Payoff Diff — {label}\n\n## 变更日志\n\n"
        diff_md += "\n".join(change_log)
        diff_md += f"\n\n## 当前健康状态\n"
        health = pm.health_check(current_chapter)
        diff_md += f"- 开放承诺: {health['open']}\n"
        diff_md += f"- 逾期承诺: {health['overdue']}\n"
        if health['overdue_ids']:
            diff_md += f"  逾期ID: {', '.join(health['overdue_ids'])}\n"
        diff_md += f"- 高优先级: {health['high_urgency']}\n"

        (run_dir / f"Promise_Payoff_Diff_{label}.md").write_text(diff_md, encoding="utf-8")
        return diff_md

    def _pm_summary(self, pm: PromisePayoffMap) -> str:
        if not pm.promises:
            return "（暂无已登记的承诺）"
        lines = ["已登记承诺："]
        for p in sorted(pm.promises.values(), key=lambda x: x.id):
            lines.append(f"- {p.id} [{p.type.value}] [{p.status.value}] 开:{p.chapter_opened}章 | {p.promise[:50]}")
        return "\n".join(lines)

    def generate_batch_report(self, batch_chapters: List[int], run_dir: Path) -> str:
        pm = self._load_map()
        current_ch = max(batch_chapters) if batch_chapters else 0
        health = pm.health_check(current_ch)

        lines = [
            f"# 承诺-回报批次报告 — 第{min(batch_chapters) if batch_chapters else 0}-{current_ch}章\n",
            f"## 当前健康状态\n",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 开放承诺 | {health['open']} |",
            f"| 逾期承诺 | {health['overdue']} |",
            f"| 高紧急度 | {health['high_urgency']} |",
            f"| 已关闭 | {health['closed']} |",
            f"| 总计 | {health['total']} |\n",
        ]

        if health['overdue_ids']:
            lines.append("## 🚨 逾期承诺（必须立即处理）\n")
            for pid in health['overdue_ids']:
                p = pm.promises[pid]
                lines.append(f"- **{pid}** [{p.type.value}]: {p.promise}")
                lines.append(f"  预计回收: {p.expected_payoff_window.start}-{p.expected_payoff_window.end}章\n")

        if health['open'] > 12:
            lines.append(f"## ⚠️ 承诺过多警告\n开放承诺 {health['open']} 条，超过推荐上限(12)。\n")

        report = "\n".join(lines)
        label = f"{min(batch_chapters):03d}_{current_ch:03d}" if batch_chapters else "000"
        (run_dir / f"Promise_Payoff_Report_{label}.md").write_text(report, encoding="utf-8")
        return report

    def run(self, task: str, run_dir: Path) -> str:
        return self.generate_batch_report([], run_dir)
