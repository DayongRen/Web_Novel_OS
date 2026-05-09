"""
agents/interactive_director.py — Interactive Director Agent

创作引导 Agent，负责把模糊创意拆解成用户可选择的问题序列，
给出候选方案，解释利弊，根据用户选择积累项目设定。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .base_agent import BaseAgent


PHASES = [
    "story_focus",       # 故事重心选择
    "protagonist",       # 主角设定
    "antagonist",        # 反派/对立力量
    "opening_style",     # 开局风格
    "pacing_preference", # 节奏偏好
    "world_depth",       # 世界观深度
    "ready",             # 收集完毕，准备生成
]


class InteractiveDirectorAgent(BaseAgent):

    role = "Interactive Director（创作引导）"
    stage = "concept"
    system_prompt = """
你是创作引导专家，负责把用户的模糊小说想法逐步引导成可生成的完整创作框架。

你的核心方式：
1. 每次只问一个最关键的问题
2. 每个问题给出 2-4 个候选选项，每个选项说明优点和风险
3. 允许用户自定义输入
4. 根据用户选择积累项目设定
5. 决定下一步应该问什么

你不是在写稿，你是在帮用户做创作决策。
每个问题都要有实际选择意义，不能问废话。
选项要具体，不能空泛。

输出格式必须是严格 JSON，不加任何 markdown 代码围栏：
{
  "phase": "当前阶段名",
  "question": "问题文本",
  "context": "为什么要问这个问题（1-2句）",
  "options": [
    {
      "id": "A",
      "label": "选项标签",
      "description": "详细描述",
      "pros": "优点",
      "cons": "风险或缺点"
    }
  ],
  "allow_custom": true,
  "collected_so_far": {}
}
"""

    def generate_first_question(self, idea: str, session_dir: Path) -> dict:
        """根据初始想法生成第一个引导问题。"""
        genre_templates = self._list_available_genres()

        prompt = f"""
用户的小说想法：
{idea}

可用类型范本：{genre_templates}

请分析这个想法，然后生成第一个最关键的引导问题。

通常第一个问题应该聚焦在"故事重心"——这个故事最核心的体验是什么。
给出 3-4 个方向清晰的选项，让用户确认方向。

严格输出 JSON，不要 markdown 围栏。
"""
        raw = self.call_llm(prompt)
        return self._parse_json(raw, "story_focus")

    def generate_next_question(self, idea: str, collected: dict, current_phase: str, session_dir: Path) -> dict:
        """根据已收集信息生成下一个问题。"""
        next_phase = self._next_phase(current_phase)

        if next_phase == "ready":
            return {
                "phase": "ready",
                "question": "好了，我已经了解得足够多了。要开始生成故事圣经和框架吗？",
                "context": "所有关键决策已完成，可以开始生成。",
                "options": [
                    {"id": "A", "label": "开始生成", "description": "生成故事圣经 + 人物设定 + 前10章章卡", "pros": "完整框架", "cons": ""},
                    {"id": "B", "label": "先生成3个故事方案", "description": "让我看看不同走向的可能性", "pros": "更多选择", "cons": "稍慢"},
                    {"id": "C", "label": "继续补充细节", "description": "我想再说说某些设定", "pros": "更精准", "cons": ""}
                ],
                "allow_custom": True,
                "collected_so_far": collected,
            }

        phase_prompts = {
            "protagonist": "主角的起点设定（身份、处境、核心欲望）",
            "antagonist": "主要对立力量（反派、障碍、或命运），以及主角为什么不能轻易越过它",
            "opening_style": "第一章的开局风格，这决定了读者对这本书的第一印象",
            "pacing_preference": "整体节奏偏好（轻快爽文 vs 细腻沉浸 vs 紧张压迫）",
            "world_depth": "世界观的厚度和重要性",
        }

        focus = phase_prompts.get(next_phase, "下一个最重要的创作决策")

        prompt = f"""
小说想法：{idea}

已收集信息：
{json.dumps(collected, ensure_ascii=False, indent=2)}

当前需要确认：{focus}

请生成针对「{focus}」的引导问题，给出 3-4 个具体选项。
选项要结合已有信息，不能脱离当前故事背景。

严格输出 JSON，phase 字段填 "{next_phase}"，不要 markdown 围栏。
"""
        raw = self.call_llm(prompt)
        return self._parse_json(raw, next_phase)

    def generate_options(self, idea: str, collected: dict, task: str, n: int, session_dir: Path) -> list[dict]:
        """生成 n 个候选方案，用于方案比较页面。"""
        prompt = f"""
小说想法：{idea}

已收集信息：
{json.dumps(collected, ensure_ascii=False, indent=2)}

任务：生成 {n} 个不同的「{task}」候选方案。

每个方案必须有明显的差异和各自的独特价值。
不要生成相似方案。

输出格式（JSON 数组，不要 markdown 围栏）：
[
  {{
    "option_id": "方案A",
    "title": "方案标题",
    "summary": "2-3句话描述核心内容",
    "key_features": ["特点1", "特点2", "特点3"],
    "pros": "优点",
    "cons": "风险/缺点",
    "best_for": "最适合哪类读者",
    "content": "方案完整内容（Markdown格式）"
  }}
]
"""
        raw = self.call_llm(prompt, temperature=0.85)
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
        return [{"option_id": "方案A", "title": "生成结果", "summary": raw[:200], "key_features": [], "pros": "", "cons": "", "best_for": "", "content": raw}]

    def integrate_user_choice(self, collected: dict, phase: str, choice_id: Optional[str], custom_text: Optional[str], options: list) -> dict:
        """将用户选择整合到 collected 字典。"""
        if custom_text:
            collected[phase] = custom_text
            return collected

        chosen = next((o for o in options if o.get("id") == choice_id), None)
        if chosen:
            collected[phase] = {
                "id": choice_id,
                "label": chosen.get("label", ""),
                "description": chosen.get("description", ""),
            }
        return collected

    def _next_phase(self, current: str) -> str:
        try:
            idx = PHASES.index(current)
            return PHASES[idx + 1] if idx + 1 < len(PHASES) else "ready"
        except ValueError:
            return "protagonist"

    def _list_available_genres(self) -> str:
        genre_dir = self.templates / "genre_profiles"
        if genre_dir.exists():
            return ", ".join(p.stem for p in genre_dir.glob("*.yaml"))
        return "urban_rebirth, xuanhuan_upgrade, infinite_flow, romance_ceo"

    def _parse_json(self, raw: str, fallback_phase: str) -> dict:
        text = raw.strip()
        for fence in ("```json", "```"):
            if text.startswith(fence):
                text = text[len(fence):]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "phase": fallback_phase,
                "question": "请告诉我更多关于这个故事的想法。",
                "context": "",
                "options": [
                    {"id": "A", "label": "继续", "description": raw[:200], "pros": "", "cons": ""}
                ],
                "allow_custom": True,
                "collected_so_far": {},
            }

    def run(self, task: str, run_dir: Path) -> str:
        return "InteractiveDirector: 请通过 generate_first_question() 调用"
