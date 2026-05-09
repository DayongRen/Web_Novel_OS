"""
Web Novel OS — Base Agent
所有专业 Agent 的基类，提供文件读写、LLM调用（通过抽象层）和分层上下文组装能力。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from llm import BaseLLMClient, make_client
from schemas.state_schema import AGENT_TEMPERATURE


class BaseAgent:
    """所有 Agent 的基类。"""

    role: str = "BaseAgent"
    system_prompt: str = ""
    stage: str = "default"

    def __init__(self, config: dict, project_root: Path, llm_client: Optional[BaseLLMClient] = None):
        self.config = config
        self.project_root = project_root
        self.repo = project_root / "project_repo"
        self.templates = project_root / "templates"
        self.max_tokens = config.get("model", {}).get("max_tokens", 8000)
        self._llm = llm_client or make_client(config)

    # ── 文件工具 ────────────────────────────────────────────────────────────

    def read_file(self, rel_path: str) -> str:
        """从 project_root 读取文件，不存在时返回空字符串。"""
        full = self.project_root / rel_path
        if full.exists():
            return full.read_text(encoding="utf-8")
        return ""

    def write_file(self, rel_path: str, content: str) -> None:
        """向 project_root 写入文件，自动创建目录。"""
        full = self.project_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")

    def append_file(self, rel_path: str, content: str) -> None:
        full = self.project_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        with open(full, "a", encoding="utf-8") as f:
            f.write(content)

    def load_yaml(self, rel_path: str) -> dict:
        full = self.project_root / rel_path
        if full.exists():
            with open(full, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def save_yaml(self, rel_path: str, data: dict) -> None:
        full = self.project_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def load_template(self, rel_path: str) -> dict:
        full = self.templates / rel_path
        if full.exists():
            with open(full, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    # ── 上下文组装（分层，避免长篇上下文爆炸） ────────────────────────────────

    def _build_base_context(self, layer: str = "full") -> str:
        """
        分层上下文组装。
        layer="global"  : 只含核心创意 + 类型配置 + 一句话圣经摘要
        layer="volume"  : global + 当前卷纲 + 当前卷承诺
        layer="local"   : volume + 最近3章摘要 + 当前开放线索
        layer="full"    : 全部（用于 Bible/Outline 阶段，章节少时可用）
        """
        parts: list[str] = []

        genre = self.config.get("genre", {}).get("primary", "")
        word_count = self.config.get("project", {}).get("target_word_count", 0)
        platform = self.config.get("project", {}).get("target_platform", "")
        parts.append(
            f"## 项目概览\n"
            f"- 类型: {genre}\n"
            f"- 目标字数: {word_count:,}\n"
            f"- 平台: {platform}\n"
            f"- 每章字数: {self.config.get('project', {}).get('words_per_chapter', 2000)}"
        )

        core_idea = self.read_file("project_repo/outlines/00_core_idea.md")
        if core_idea:
            parts.append(f"## 核心创意\n{core_idea}")

        if layer in ("global", "volume", "local", "full"):
            story_bible = self.read_file("project_repo/canon/Story_Bible.md")
            if story_bible and "待 Bible 阶段填充" not in story_bible:
                parts.append(f"## 故事圣经\n{self._truncate(story_bible, 2000)}")

        if layer in ("full",):
            for path, label in [
                ("project_repo/canon/World_Bible.md", "世界观"),
                ("project_repo/canon/Character_Bible.md", "人物设定"),
                ("project_repo/canon/Power_System.md", "力量体系"),
                ("project_repo/canon/Faction_Map.md", "势力地图"),
                ("project_repo/canon/Timeline.md", "时间线"),
                ("project_repo/canon/Relationship_Map.md", "关系图"),
            ]:
                content = self.read_file(path)
                if content and "待 Bible 阶段填充" not in content:
                    parts.append(f"## {label}\n{self._truncate(content, 3000)}")

            for path, label in [
                ("project_repo/outlines/03_full_outline.md", "全书总纲"),
                ("project_repo/outlines/04_volume_outlines.md", "分卷纲"),
            ]:
                content = self.read_file(path)
                if content:
                    parts.append(f"## {label}\n{self._truncate(content, 4000)}")

        if layer in ("volume", "local", "full"):
            ch_outlines = self.read_file("project_repo/outlines/05_chapter_outlines.md")
            if ch_outlines:
                parts.append(f"## 章节大纲\n{self._truncate(ch_outlines, 3000)}")

            pp_map = self.read_file("project_repo/continuity/Promise_Payoff_Map.yaml")
            if pp_map and "promises: []" not in pp_map:
                parts.append(f"## 承诺-回报追踪\n```yaml\n{self._truncate(pp_map, 2000)}\n```")

        if layer in ("local", "full"):
            open_threads = self.read_file("project_repo/continuity/Open_Threads.md")
            if open_threads:
                parts.append(f"## 悬挂线索\n{self._truncate(open_threads, 1500)}")

            arc_tracker = self.read_file("project_repo/continuity/Character_Arc_Tracker.yaml")
            if arc_tracker and "characters: []" not in arc_tracker:
                parts.append(f"## 人物弧追踪\n```yaml\n{self._truncate(arc_tracker, 1500)}\n```")

        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + f"\n\n[... 内容已截断，完整版见文件 ...]"

    def _load_genre_template(self) -> str:
        genre = self.config.get("genre", {}).get("primary", "")
        if not genre:
            return ""
        tpl = self.load_template(f"genre_profiles/{genre}.yaml")
        if tpl:
            return f"## 类型范本 ({genre})\n```yaml\n{yaml.dump(tpl, allow_unicode=True)}```"
        return ""

    def _load_beat_sheet(self) -> str:
        bs_name = self.config.get("structure", {}).get("beat_sheet", "")
        if not bs_name:
            return ""
        tpl = self.load_template(f"beat_sheets/{bs_name}.yaml")
        if tpl:
            return f"## 节奏模板 ({bs_name})\n```yaml\n{yaml.dump(tpl, allow_unicode=True)}```"
        return ""

    # ── LLM 调用 ────────────────────────────────────────────────────────────

    def _get_temperature(self) -> float:
        """根据 stage 返回阶段特化的 temperature，而非全局 0.85。"""
        return AGENT_TEMPERATURE.get(self.stage, AGENT_TEMPERATURE["default"])

    def _build_full_system(self) -> str:
        master = self.read_file("system_prompt.md")
        return f"{master}\n\n## 当前角色\n你现在扮演的是：{self.role}\n\n{self.system_prompt}"

    def call_llm(self, user_message: str, extra_system: str = "", temperature: Optional[float] = None) -> str:
        """通过抽象 LLM 客户端发送请求，返回文本响应。"""
        system = self._build_full_system()
        if extra_system:
            system = f"{system}\n\n{extra_system}"
        temp = temperature if temperature is not None else self._get_temperature()
        resp = self._llm.complete(
            system=system,
            user=user_message,
            max_tokens=self.max_tokens,
            temperature=temp,
        )
        return resp.text

    def run(self, task: str, run_dir: Path) -> str:
        """子类重写此方法，执行具体任务。"""
        raise NotImplementedError
