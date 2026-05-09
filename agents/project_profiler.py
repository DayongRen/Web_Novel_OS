"""
agents/project_profiler.py — Project Profiler Agent

第一步 Agent：分析用户输入，生成 Project_Profile.yaml。
不依赖任何已有大纲，纯粹从 idea + 用户参数推断。
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .base_agent import BaseAgent
from schemas.project_profile import (
    ProjectProfile, ReaderContract, ProductionHints, RiskProfile,
    determine_length_class, determine_card_policy
)


class ProjectProfilerAgent(BaseAgent):

    role = "Project Profiler（项目画像生成）"
    stage = "concept"
    system_prompt = """
你是项目画像分析师。给定用户的小说想法和基本参数，你需要识别：

1. 这是什么类型（主类型 + 辅助类型）？
2. 这是人物驱动还是情节驱动还是世界观驱动？
3. 读者最核心的期待是什么（情感回报 / 爽感 / 智识满足）？
4. 需要哪些账本（伏笔/案件/战力/感情线/势力/资源）？
5. 最大的创作风险在哪里？

输出 JSON，不要 markdown 围栏：
{
  "genre_primary": "",
  "genre_secondary": [],
  "tone": "",
  "heat_level": "low|medium|high",
  "complexity": "simple|medium|complex|epic",
  "audience": "",
  "reader_contract": {
    "main_hook": "",
    "core_expectation": "",
    "emotional_payoff": "",
    "plot_payoff": ""
  },
  "risk_profile": {
    "biggest_risks": [],
    "required_ledgers": [],
    "required_quality_gates": []
  },
  "structure_hint": "",
  "needs_world_bible": true,
  "needs_power_system": false,
  "needs_faction_ledger": false,
  "needs_case_ledger": false,
  "needs_romance_arc": false,
  "needs_resource_ledger": false,
  "needs_instance_ledger": false
}
"""

    PROFILE_PATH = "project_repo/manifests/Project_Profile.yaml"

    def generate_profile(
        self,
        idea: str,
        title: str,
        target_word_count: int,
        target_platform: str,
        automation_level: str,
        run_dir: Path,
    ) -> ProjectProfile:

        length_class = determine_length_class(target_word_count)
        genre_hint = self._detect_genre_from_idea(idea)

        prompt = f"""
小说想法：
{idea}

基本参数：
- 目标字数：{target_word_count:,}字
- 长度分级：{length_class}
- 目标平台：{target_platform or '通用网文'}
- 自动化程度：{automation_level}
- 初步类型判断（仅供参考）：{genre_hint}

请分析这个项目，生成项目画像 JSON。
仔细思考：这本书最核心的阅读吸引力是什么？读者会因为什么继续看下去？
"""
        raw = self.call_llm(prompt, temperature=0.4)
        analysis = self._parse_json(raw)

        profile = ProjectProfile(
            title=title,
            original_idea=idea,
            target_word_count=target_word_count,
            target_platform=target_platform,
            language="zh",
            genre_primary=analysis.get("genre_primary", genre_hint),
            genre_secondary=analysis.get("genre_secondary", []),
            tone=analysis.get("tone", ""),
            heat_level=analysis.get("heat_level", "medium"),
            complexity=analysis.get("complexity", "medium"),
            audience=analysis.get("audience", ""),
            length_class=length_class,
            reader_contract=ReaderContract(
                main_hook=analysis.get("reader_contract", {}).get("main_hook", ""),
                core_expectation=analysis.get("reader_contract", {}).get("core_expectation", ""),
                emotional_payoff=analysis.get("reader_contract", {}).get("emotional_payoff", ""),
                plot_payoff=analysis.get("reader_contract", {}).get("plot_payoff", ""),
            ),
            production=ProductionHints(
                automation_level=automation_level,
                batch_size=3 if length_class == "short_30k" else 5,
                chapter_card_policy=determine_card_policy(length_class),
            ),
            risk=RiskProfile(
                biggest_risks=analysis.get("risk_profile", {}).get("biggest_risks", []),
                required_ledgers=analysis.get("risk_profile", {}).get("required_ledgers", []),
                required_quality_gates=analysis.get("risk_profile", {}).get("required_quality_gates", []),
            ),
        )

        # 覆盖 LLM 分析的 needs 字段（如果有的话）
        if "needs_world_bible" in analysis:
            profile.needs_world_bible = analysis["needs_world_bible"]
        if "needs_power_system" in analysis:
            profile.needs_power_system = analysis["needs_power_system"]
        if "needs_faction_ledger" in analysis:
            profile.needs_faction_ledger = analysis["needs_faction_ledger"]
        if "needs_case_ledger" in analysis:
            profile.needs_case_ledger = analysis["needs_case_ledger"]
        if "needs_romance_arc" in analysis:
            profile.needs_romance_arc = analysis["needs_romance_arc"]
        if "needs_resource_ledger" in analysis:
            profile.needs_resource_ledger = analysis["needs_resource_ledger"]
        if "needs_instance_ledger" in analysis:
            profile.needs_instance_ledger = analysis["needs_instance_ledger"]

        profile_path = self.project_root / self.PROFILE_PATH
        profile.save(profile_path)

        run_copy = run_dir / "Project_Profile.yaml"
        profile.save(run_copy)

        return profile

    def _detect_genre_from_idea(self, idea: str) -> str:
        """简单关键词检测，辅助 LLM 理解类型。"""
        idea_l = idea.lower()
        if any(w in idea_l for w in ["修炼", "灵气", "境界", "丹药", "宗门", "仙"]):
            return "xianxia"
        if any(w in idea_l for w in ["玄幻", "斗气", "魔法", "修炼", "升级", "系统"]):
            return "fantasy_xuanhuan"
        if any(w in idea_l for w in ["重生", "穿越", "都市", "商业", "打脸"]):
            return "urban_rebirth"
        if any(w in idea_l for w in ["言情", "总裁", "爱情", "婚", "恋"]):
            return "romance"
        if any(w in idea_l for w in ["宫", "皇", "朝廷", "权谋", "太后", "嫔妃"]):
            return "palace_intrigue"
        if any(w in idea_l for w in ["悬疑", "推理", "案件", "凶手", "死亡调查"]):
            return "suspense"
        if any(w in idea_l for w in ["副本", "游戏", "无限", "任务", "末日"]):
            return "infinite_flow"
        if any(w in idea_l for w in ["种田", "农场", "古代", "庄稼", "穿越古"]):
            return "historical_farming"
        return "urban_rebirth"

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
        return "ProjectProfiler: 请通过 generate_profile() 调用"
