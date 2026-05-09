"""
agents/production_strategy_agent.py — Production Strategy Agent

读取 ProjectProfile + 三组模板（长度/题材/平台），
生成完整的 Production_Strategy.yaml。
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .base_agent import BaseAgent
from schemas.project_profile import ProjectProfile
from schemas.production_strategy import (
    ProductionStrategy, ChapterCardPolicy, BatchPolicy,
    QualityPolicy, FailurePolicy, StageDefinition, ExportConfig
)


class ProductionStrategyAgent(BaseAgent):

    role = "Production Strategy Agent（生产策略生成）"
    stage = "concept"
    system_prompt = """
你是生产策略设计师。根据项目画像和三组模板，生成最优的生产策略。

策略要回答：
1. 每批写多少章？
2. 多久做一次结构复盘？
3. 需要哪些质量门？
4. 章节卡片用哪种模式？
5. 每次导出哪些产物？
6. 最大的失败风险和恢复策略？

输出 JSON，不要 markdown 围栏：
{
  "words_per_chapter": 2000,
  "batch_size": 5,
  "review_interval": 20,
  "major_review_interval": 50,
  "snapshot_interval": 10,
  "active_quality_gates": ["universal", "length_specific", "genre_specific"],
  "additional_hard_fail_gates": [],
  "additional_warn_gates": [],
  "export_artifacts": ["final.md", "final.txt"],
  "notes": ""
}
"""

    STRATEGY_PATH = "project_repo/manifests/Production_Strategy.yaml"

    def generate_strategy(
        self,
        profile: ProjectProfile,
        run_dir: Path,
    ) -> ProductionStrategy:

        length_profile = self._load_length_profile(profile.length_class)
        genre_profile = self._load_genre_profile(profile.genre_primary)
        platform_profile = self._load_platform_profile(profile.target_platform)

        prompt = f"""
## 项目画像
{yaml.dump(profile.to_dict(), allow_unicode=True, default_flow_style=False)[:2000]}

## 长度模板 ({profile.length_class})
{yaml.dump(length_profile, allow_unicode=True)[:800]}

## 题材模板 ({profile.genre_primary})
{yaml.dump(genre_profile, allow_unicode=True)[:800]}

## 平台模板 ({profile.target_platform or 'web_serial_general'})
{yaml.dump(platform_profile, allow_unicode=True)[:600]}

请结合以上三组模板，生成最优生产策略 JSON。
重点考虑：
- 这个项目的最大风险是什么？策略如何防范？
- 这个长度下复盘频率应该多高？
- 这个题材需要哪些专属质量门？
"""
        raw = self.call_llm(prompt, temperature=0.3)
        hints = self._parse_json(raw)

        base = ProductionStrategy.default_for_profile(profile)

        wpc = hints.get("words_per_chapter", base.words_per_chapter)
        if 800 <= wpc <= 6000:
            base.words_per_chapter = wpc

        bp = hints.get("batch_size", base.batch_policy.write_batch_size)
        if 2 <= bp <= 10:
            base.batch_policy.write_batch_size = bp
            base.batch_policy.quality_check_every = bp

        ri = hints.get("review_interval", base.batch_policy.structural_review_every)
        if 5 <= ri <= 100:
            base.batch_policy.structural_review_every = ri

        mri = hints.get("major_review_interval", base.batch_policy.major_reoutline_every)
        if mri > ri:
            base.batch_policy.major_reoutline_every = mri

        si = hints.get("snapshot_interval", base.batch_policy.snapshot_every)
        if 3 <= si <= 50:
            base.batch_policy.snapshot_every = si

        active_gates = hints.get("active_quality_gates", base.quality_policy.active_gates)
        base.quality_policy.active_gates = active_gates

        extra_hard = hints.get("additional_hard_fail_gates", [])
        base.quality_policy.hard_fail = list(dict.fromkeys(
            base.quality_policy.hard_fail + extra_hard
        ))

        extra_warn = hints.get("additional_warn_gates", [])
        base.quality_policy.warn_only = list(dict.fromkeys(
            base.quality_policy.warn_only + extra_warn
        ))

        artifacts = hints.get("export_artifacts", base.export_config.artifacts)
        base.export_config.artifacts = artifacts

        base.notes = hints.get("notes", "")

        genre_ledgers = list(genre_profile.get("required_ledgers", []))
        base.required_ledgers = list(dict.fromkeys(base.required_ledgers + genre_ledgers))

        base.active_agents = self._determine_agents(profile)

        strategy_path = self.project_root / self.STRATEGY_PATH
        base.save(strategy_path)
        run_copy = run_dir / "Production_Strategy.yaml"
        base.save(run_copy)

        return base

    def _determine_agents(self, profile: ProjectProfile) -> list[str]:
        agents = [
            "ProjectProfilerAgent", "PlotArchitectAgent",
            "CharacterKeeperAgent", "ChapterWriterAgent",
            "ContinuityCheckerAgent", "PromisePayoffValidatorAgent",
            "PacingDoctorAgent",
        ]
        if profile.needs_world_bible:
            agents.append("WorldbuildingKeeperAgent")
        if profile.needs_power_system:
            agents.append("PowerSystemDesignerAgent")
        if profile.needs_faction_ledger:
            agents.append("FactionLogicAgent")
        if profile.needs_case_ledger:
            agents.append("CaseLogicAgent")
        if profile.needs_romance_arc:
            agents.append("RomanceArcAgent")
        if profile.needs_resource_ledger:
            agents.append("ResourceEconomyAgent")
        if profile.needs_instance_ledger:
            agents.append("InstanceDesignerAgent")
        if profile.length_class not in ("short_30k",):
            agents.append("StyleKeeperAgent")
        return agents

    def _load_length_profile(self, length_class: str) -> dict:
        return self.load_template(f"length_profiles/{length_class}.yaml")

    def _load_genre_profile(self, genre: str) -> dict:
        d = self.load_template(f"genre_profiles/{genre}.yaml")
        if not d:
            d = self.load_template("genre_profiles/urban_rebirth.yaml")
        return d or {}

    def _load_platform_profile(self, platform: str) -> dict:
        name = platform or "web_serial_general"
        d = self.load_template(f"platform_profiles/{name}.yaml")
        if not d:
            d = self.load_template("platform_profiles/web_serial_general.yaml")
        return d or {}

    def _parse_json(self, raw: str) -> dict:
        text = raw.strip()
        for fence in ("```json", "```"):
            if text.startswith(fence):
                text = text[len(fence):]
        if text.endswith("```"):
            text = text[:-3]
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return {}

    def run(self, task: str, run_dir: Path) -> str:
        return "ProductionStrategyAgent: 请通过 generate_strategy() 调用"
