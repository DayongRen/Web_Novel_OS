"""
Showrunner Agent — 总编剧
把控全局故事方向，协调各 Agent，确保核心卖点不偏离。
"""

from pathlib import Path

from .base_agent import BaseAgent


class ShowrunnerAgent(BaseAgent):

    role = "Showrunner（总编剧）"
    system_prompt = """
你是这部小说的总编剧（Showrunner），相当于美剧的 Showrunner 或电影的总导演。

你的核心职责：
1. 守住故事的核心卖点和类型承诺
2. 每轮最多提出3个 major 修改目标
3. 确保各 Agent 的产出不偏离整体方向
4. 识别故事中的结构性风险（崩设定、崩人物、承诺未回收）
5. 生成项目审计报告和阶段性方向指导

你不直接写正文，但你对所有内容有最终决策权。
每次审核都要问：这是否符合类型承诺？读者会不会失望？
"""

    def audit_project(self, run_dir: Path) -> str:
        context = self._build_base_context()
        genre_tpl = self._load_genre_template()
        beat_sheet = self._load_beat_sheet()

        prompt = f"""
{context}

{genre_tpl}

{beat_sheet}

## 任务：项目审计

请对当前项目进行全面审计，输出以下内容：

### 1. 项目概览
- 类型定位是否准确
- 核心卖点识别（列出3-5个）
- 目标读者匹配度

### 2. 结构分析
- 当前篇幅目标是否合理
- 分卷节奏规划是否符合类型惯例
- 前三章钩子设计是否到位

### 3. 风险识别
- 设定崩塌风险（HIGH/MEDIUM/LOW）
- 人物扁平化风险
- 读者流失风险（标出最可能弃书的位置）
- 类型承诺兑现风险

### 4. 本阶段最多3个主要目标
明确写出本轮创作最关键的3件事。

### 5. 总编剧指令
给所有其他 Agent 的协调指令。

输出格式为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Project_Audit.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def generate_direction(self, stage: str, run_dir: Path) -> str:
        context = self._build_base_context()
        prompt = f"""
{context}

## 任务：{stage} 阶段方向指导

当前处于 {stage} 阶段。

请生成：
1. 本阶段核心任务（最多3条）
2. 各 Agent 的具体指令
3. 本阶段完成后的验收标准
4. 需要重点守住的类型承诺

输出格式：Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / f"Showrunner_{stage}_Direction.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def run(self, task: str, run_dir: Path) -> str:
        if task == "audit":
            return self.audit_project(run_dir)
        return self.generate_direction(task, run_dir)
