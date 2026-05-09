"""
agents/agent_router.py — Agent 路由器

读取 Project_Profile + Production_Strategy，
返回本次运行应该激活的 Agent 实例集合。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from schemas.project_profile import ProjectProfile
from schemas.production_strategy import ProductionStrategy
from llm import BaseLLMClient, make_client


class AgentRouter:
    """根据项目画像和生产策略决定激活哪些 Agent。"""

    def __init__(self, config: dict, project_root: Path, llm_client: Optional[BaseLLMClient] = None):
        self.config = config
        self.project_root = project_root
        self._client = llm_client or make_client(config)
        self._agent_cache: dict = {}

    def _get_agent(self, cls_name: str):
        if cls_name in self._agent_cache:
            return self._agent_cache[cls_name]

        import agents as ag_module
        cls = getattr(ag_module, cls_name, None)
        if cls is None:
            return None
        instance = cls(self.config, self.project_root, self._client)
        self._agent_cache[cls_name] = instance
        return instance

    def load_profile(self) -> Optional[ProjectProfile]:
        path = self.project_root / "project_repo/manifests/Project_Profile.yaml"
        if path.exists():
            return ProjectProfile.load(path)
        return None

    def load_strategy(self) -> Optional[ProductionStrategy]:
        path = self.project_root / "project_repo/manifests/Production_Strategy.yaml"
        return ProductionStrategy.load(path)

    def get_active_agents(self, strategy: Optional[ProductionStrategy] = None) -> dict:
        """返回各角色对应的 Agent 实例字典。"""
        if strategy is None:
            strategy = self.load_strategy()

        active_names = set(strategy.active_agents if strategy else [])

        # 始终激活的核心 Agent
        always_active = [
            "ShowrunnerAgent",
            "PlotArchitectAgent",
            "CharacterKeeperAgent",
            "ChapterWriterAgent",
            "ContinuityCheckerAgent",
            "PromisePayoffValidatorAgent",
            "PacingDoctorAgent",
        ]
        all_names = list(dict.fromkeys(always_active + list(active_names)))

        result = {}
        for name in all_names:
            agent = self._get_agent(name)
            if agent:
                result[name] = agent

        return result

    def get_chapter_writer(self):
        return self._get_agent("ChapterWriterAgent")

    def get_continuity_checker(self):
        return self._get_agent("ContinuityCheckerAgent")

    def get_pacing_doctor(self):
        return self._get_agent("PacingDoctorAgent")

    def get_promise_validator(self):
        return self._get_agent("PromisePayoffValidatorAgent")

    def get_plot_architect(self):
        return self._get_agent("PlotArchitectAgent")

    def get_character_keeper(self):
        return self._get_agent("CharacterKeeperAgent")

    def get_worldbuilding_keeper(self):
        return self._get_agent("WorldbuildingKeeperAgent")

    def get_power_system_designer(self):
        return self._get_agent("PowerSystemDesignerAgent")

    def get_commercial_hook(self):
        return self._get_agent("CommercialHookAgent")

    def get_style_keeper(self):
        return self._get_agent("StyleKeeperAgent")

    def get_red_team(self):
        return self._get_agent("RedTeamReviewerAgent")

    def summary(self, strategy: Optional[ProductionStrategy] = None) -> str:
        agents = self.get_active_agents(strategy)
        lines = ["激活的 Agent:"]
        for name in agents:
            lines.append(f"  ✅ {name}")
        inactive = [
            n for n in [
                "PowerSystemDesignerAgent", "WorldbuildingKeeperAgent",
                "StyleKeeperAgent", "CommercialHookAgent",
            ]
            if n not in agents
        ]
        for name in inactive:
            lines.append(f"  ⏭️  {name} (跳过)")
        return "\n".join(lines)
