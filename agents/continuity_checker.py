"""
Continuity Checker Agent — 连续性检查器
检查时间线、人物状态、道具归属、伤势恢复、前后设定矛盾。
"""

from pathlib import Path
from typing import List

from .base_agent import BaseAgent


class ContinuityCheckerAgent(BaseAgent):

    role = "Continuity Checker（连续性检查器）"
    system_prompt = """
你是连续性检查器，负责维护长篇小说的内部一致性。

你的职责：
1. 检查时间线连续性（某事件不能在前因之前发生）
2. 检查人物状态连续性（受伤的人不能突然完好）
3. 检查道具归属连续性（道具不能无故消失或出现）
4. 检查地点连续性（移动时间是否合理）
5. 检查设定连续性（规则不能前后矛盾）
6. 检查信息连续性（人物不能知道不该知道的事）

这是长篇小说最容易出错的地方，必须严格检查。
"""

    def check_batch(self, chapters: List[dict], run_dir: Path) -> str:
        context = self._build_base_context()
        timeline = self.read_file("project_repo/canon/Timeline.md")
        item_ledger = self.read_file("project_repo/canon/Item_Ledger.md")

        chapters_text = "\n\n".join(
            f"### 第{ch['num']}章\n{ch['content']}" for ch in chapters
        )

        prompt = f"""
{context}

## 当前时间线
{timeline}

## 道具账本
{item_ledger}

## 待检查章节内容
{chapters_text}

## 任务：连续性全面检查

### 1. 时间线检查
- 本批次章节发生在故事内哪些时间段？
- 是否有时间跳跃不合理的地方？
- 是否与已有时间线冲突？

### 2. 人物状态检查
对每个主要出场人物：
- 其伤势/状态是否与前文一致？
- 其位置是否合理？
- 是否出现在不该出现的地方？

### 3. 道具与资源检查
- 是否有道具无故消失？
- 是否有资源无故增加？
- 道具的归属是否一致？

### 4. 设定一致性检查
- 是否有与 World_Bible 冲突的描述？
- 是否有与 Power_System 冲突的战力描述？
- 是否有规则被随意打破？

### 5. 信息一致性检查
- 是否有角色知道不该知道的信息？
- 是否有信息被错误重复（前文已揭露但写成首次揭露）？

### 6. 问题汇总
| 问题 | 所在章节 | 严重程度 | 修复建议 |
|------|---------|---------|---------|

### 7. 需要更新的 Canon 文件
本批次新增了哪些需要写入 Canon 的信息？

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        ch_range = f"{chapters[0]['num']:03d}_{chapters[-1]['num']:03d}" if chapters else "000_000"
        out_path = run_dir / f"Continuity_Report_{ch_range}.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def update_open_threads(self, run_dir: Path) -> str:
        context = self._build_base_context()
        existing_threads = self.read_file("project_repo/continuity/Open_Threads.md")
        mystery_ledger = self.read_file("project_repo/continuity/Mystery_Ledger.yaml")
        foreshadowing = self.read_file("project_repo/continuity/Foreshadowing_Ledger.yaml")

        prompt = f"""
{context}

## 现有开放线索
{existing_threads}

## 谜团账本
{mystery_ledger}

## 伏笔账本
{foreshadowing}

## 任务：更新开放线索列表

基于当前所有可用信息，生成最新的 Open_Threads.md：

# 开放线索总表

## 主线悬挂线索
（对主线走向有重大影响的未解决问题）

## 支线悬挂线索
（支线中的未解决问题）

## 人物悬挂线索
（人物关系或背景中的未解决问题）

## 世界观悬挂线索
（世界设定中留下的谜团）

## 即将到期线索
（预计在近5-10章内应该回收的线索）

## 长期伏笔
（设计为全书都在发酵的伏笔）

输出完整的 Open_Threads.md 内容，Markdown格式，中文。
"""
        result = self.call_llm(prompt)
        repo_path = self.project_root / "project_repo/continuity/Open_Threads.md"
        repo_path.write_text(result, encoding="utf-8")
        return result

    def run(self, task: str, run_dir: Path) -> str:
        if task == "update_threads":
            return self.update_open_threads(run_dir)
        return self.update_open_threads(run_dir)
