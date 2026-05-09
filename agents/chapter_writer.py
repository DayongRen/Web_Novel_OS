"""
Chapter Writer Agent — 章节写手
根据结构化 ChapterCard 生成正文，不再接受整份章纲文本。
"""

from pathlib import Path
from typing import Optional

from .base_agent import BaseAgent
from llm import BaseLLMClient
from schemas.chapter_card_schema import ChapterCard, ChapterCardIndex


class ChapterWriterAgent(BaseAgent):

    role = "Chapter Writer（章节写手）"
    stage = "chapters"
    system_prompt = """
你是章节写手，专职根据结构化章节卡片（ChapterCard）生成高质量中文网文正文。

⚠️ 严格约束：
1. 必须按章节卡片执行，不能自行添加或删除主要情节节点
2. 不能引入卡片中没有的重要新人物（次要人物可以）
3. 不能改变已确认的世界观设定
4. 章节结尾必须有明确的钩子

写作标准：
- 场景感：读者能在脑海中看到画面
- 节奏感：对话和动作交替，不拖沓
- 人物感：对话符合角色声音特征
- 情绪感：读者能感受到情绪变化
- 钩子感：结尾最后一句必须有张力

直接输出正文，以章节标题开头，不要有任何额外说明。
"""

    def __init__(self, config: dict, project_root: Path, llm_client: Optional[BaseLLMClient] = None):
        super().__init__(config, project_root, llm_client)
        self._card_index: Optional[ChapterCardIndex] = None

    def _get_card_index(self) -> ChapterCardIndex:
        if self._card_index is None:
            card_path = self.project_root / "project_repo/outlines/chapter_cards.yaml"
            self._card_index = ChapterCardIndex(card_path if card_path.exists() else None)
        return self._card_index

    def write_chapter(
        self,
        chapter_num: int,
        chapter_card: ChapterCard,
        run_dir: Path,
        volume_dir: Path,
    ) -> str:
        context = self._build_base_context(layer="local")
        voice_guide = self.read_file("project_repo/style/Voice_Guide.md")
        pov_rules = self.read_file("project_repo/style/POV_Rules.md")
        forbidden = self.read_file("project_repo/style/Forbidden_Cliches.md")
        words_per_chapter = chapter_card.word_target or self.config.get("project", {}).get("words_per_chapter", 2000)
        prev_chapters_text = self._get_recent_chapters(chapter_num, 2)

        style_context = ""
        if voice_guide and "待" not in voice_guide[:20]:
            style_context += f"\n## 文风指南\n{self._truncate(voice_guide, 1000)}"
        if pov_rules:
            style_context += f"\n## 视角规则\n{self._truncate(pov_rules, 500)}"
        if forbidden:
            style_context += f"\n## 禁用套路\n{self._truncate(forbidden, 800)}"

        prompt = f"""
{context}

{style_context}

## 前置章节（连续性参考）
{prev_chapters_text}

{chapter_card.to_prompt_text()}

## 写作任务

请根据上方章节卡片，写第{chapter_num}章完整正文。

要求：
- 目标字数：约{words_per_chapter}字（±20%可接受）
- 完整正文，不是大纲或摘要
- 开头迅速进入状态，不要大段背景介绍
- 对话要鲜活，体现不同角色的声音差异
- 章节结尾钩子：{chapter_card.ending_hook or '（必须有明确的前向悬念）'}

直接输出正文，以"第{chapter_num}章" + 章节标题开头。
"""
        result = self.call_llm(prompt)

        chapter_file = volume_dir / f"ch{chapter_num:03d}.md"
        chapter_file.parent.mkdir(parents=True, exist_ok=True)
        chapter_file.write_text(result, encoding="utf-8")

        run_chapter = run_dir / f"ch{chapter_num:03d}.md"
        run_chapter.write_text(result, encoding="utf-8")
        return result

    def _get_recent_chapters(self, current_num: int, count: int) -> str:
        parts = []
        manuscript = self.project_root / "project_repo/manuscript"
        for i in range(max(1, current_num - count), current_num):
            if manuscript.exists():
                for vol_dir in sorted(manuscript.iterdir()):
                    if vol_dir.is_dir():
                        ch_file = vol_dir / f"ch{i:03d}.md"
                        if ch_file.exists():
                            content = ch_file.read_text(encoding="utf-8")
                            parts.append(f"### 第{i}章（节选后500字）\n...{content[-500:]}")
                            break
        return "\n\n".join(parts) if parts else "（无前置章节）"

    def run(self, task: str, run_dir: Path) -> str:
        return "ChapterWriter: 请通过 write_chapter(chapter_num, chapter_card, ...) 调用"
