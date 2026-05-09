"""
Style Keeper Agent — 文风守护者
统一文风，防止不同章节像不同作者写的。
"""

from pathlib import Path
from typing import List

from .base_agent import BaseAgent


class StyleKeeperAgent(BaseAgent):

    role = "Style Keeper（文风守护者）"
    system_prompt = """
你是文风守护者，负责维护整部小说的风格一致性。

你的职责：
1. 建立并维护 Voice_Guide.md
2. 检查章节之间的文风一致性
3. 统一叙述视角
4. 统一句式密度和段落节奏
5. 统一情绪基调（幽默/压迫/暧昧/热血）
6. 防止不同章节像不同作者写的

判断维度：
- 叙述视角是否一致
- 句子平均长度和节奏
- 形容词使用习惯
- 情绪表达方式
- 动作描写风格
- 心理描写比例
"""

    def build_voice_guide(self, run_dir: Path) -> str:
        context = self._build_base_context()
        genre_tpl = self._load_genre_template()
        genre_tone = self.read_file("project_repo/style/Genre_Tone.md")
        sample = self.read_file("project_repo/style/Sample_Passages.md")

        prompt = f"""
{context}

{genre_tpl}

## 类型基调
{genre_tone}

## 示范段落
{sample}

## 任务：建立文风指南（Voice Guide）

请为本小说建立完整的文风规范文档：

### 一、叙述视角
- 主要视角（第几人称，有限/全知）
- 视角切换规则（何时可以切换）

### 二、叙述风格
- 句式特征（长句/短句/混合，比例建议）
- 段落长度（几句为一段）
- 叙述节奏（快节奏打斗场景 vs 慢节奏情感场景）

### 三、语言特征
- 核心词汇风格（书面/口语/网文特色词）
- 形容词使用原则
- 动作描写风格
- 环境描写原则（多少字算合适）

### 四、心理描写
- 比例（占全文的X%）
- 方式（直接/隐晦/行为化）

### 五、情绪基调
- 整体基调
- 不同场景的基调变化规则

### 六、禁用风格
明确列出不应出现的写法：
- 不允许的句式
- 不允许的叙述习惯
- 不允许的情绪表达方式

### 七、示范对比
- 错误写法示例（1-2例）
- 正确写法示例（1-2例）

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Voice_Guide.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/style/Voice_Guide.md"
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        repo_path.write_text(result, encoding="utf-8")
        return result

    def check_style_consistency(self, chapters: List[dict], run_dir: Path) -> str:
        voice_guide = self.read_file("project_repo/style/Voice_Guide.md")
        chapters_text = "\n\n---\n\n".join(
            f"### 第{ch['num']}章（节选）\n{ch['content'][:800]}" for ch in chapters
        )

        prompt = f"""
## 文风指南
{voice_guide}

## 待检查章节（各章节选）
{chapters_text}

## 任务：文风一致性检查

### 1. 逐章文风评估
对每章：
- 叙述视角是否一致
- 句式风格是否吻合
- 情绪基调是否一致
- 是否有明显的"换作者"感

### 2. 文风偏差列举
具体指出偏离 Voice Guide 的段落或写法。

### 3. 跨章一致性评级
整体一致性：A/B/C/D

### 4. 修复建议
针对每处偏差给出具体修改方向。

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        ch_range = f"{chapters[0]['num']:03d}_{chapters[-1]['num']:03d}" if chapters else "000_000"
        out_path = run_dir / f"Style_Consistency_Report_{ch_range}.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def run(self, task: str, run_dir: Path) -> str:
        if task == "build_guide":
            return self.build_voice_guide(run_dir)
        return self.build_voice_guide(run_dir)
