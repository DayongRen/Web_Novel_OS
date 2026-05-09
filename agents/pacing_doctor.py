"""
Pacing Doctor Agent — 节奏医生
检查节奏、爽点间隔、信息密度，标记水章。
"""

from pathlib import Path
from typing import List

from .base_agent import BaseAgent


class PacingDoctorAgent(BaseAgent):

    role = "Pacing Doctor（节奏医生）"
    system_prompt = """
你是节奏医生，专门诊断小说的节奏问题。

你的职责：
1. 检查每章是否有冲突
2. 检查爽点间隔是否符合配置
3. 检查信息密度是否过高或过低
4. 检测水章（无效章节）
5. 检查章节尾钩子质量
6. 给出具体的节奏修复建议

水章定义：
- 只有设定解说，没有冲突
- 只有人物闲聊，没有推进
- 重复之前已有的信息
- 没有情绪变化
- 没有任何承诺被开启或关闭

评级：
- A：节奏完美，钩子有力，冲突清晰
- B：节奏良好，有轻微问题
- C：节奏拖沓，需要修剪或加强冲突
- D：水章，需要大改或删除
"""

    def check_batch_pacing(self, chapters: List[dict], run_dir: Path) -> str:
        context = self._build_base_context()
        pacing_config = self.config.get("pacing", {})
        genre_tpl = self._load_genre_template()

        chapters_text = ""
        for ch in chapters:
            chapters_text += f"\n\n### 第{ch['num']}章：{ch.get('title', '')}\n{ch['content'][:1200]}...\n"

        prompt = f"""
{context}

{genre_tpl}

## 节奏配置
小爽点间隔：每{pacing_config.get('small_payoff_every_chapters', 2)}章
中爽点间隔：每{pacing_config.get('medium_payoff_every_chapters', 8)}章
大爽点间隔：每{pacing_config.get('major_payoff_every_chapters', 30)}章
是否必须有钩子：{pacing_config.get('cliffhanger_required', True)}
最大说明文字比例：{pacing_config.get('max_exposition_ratio', 0.18)}

## 待检查章节
{chapters_text}

## 任务：节奏诊断报告

请对每一章进行节奏诊断：

### 逐章评级
对每章输出：
- 第X章 | 评级（A/B/C/D） | 冲突强度（高/中/低/无） | 钩子强度（强/中/弱/无） | 主要问题

### 批次整体分析
1. **爽点分布**：这批章节中的爽点分布是否合理？
2. **节奏曲线**：张弛是否合理（不能一直高，也不能一直低）？
3. **水章识别**：标出所有评级为C或D的章节及原因
4. **钩子质量**：哪章的钩子最强？哪章最弱？

### 修复建议
对每个C/D评级章节给出具体修复方案：
- 问题所在
- 解决方向（加冲突/删废话/改钩子/拆分/合并）
- 优先级（HIGH/MEDIUM/LOW）

### 下批次节奏建议
基于当前节奏状态，下批次应该做什么？

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        ch_range = f"{chapters[0]['num']:03d}_{chapters[-1]['num']:03d}" if chapters else "000_000"
        out_path = run_dir / f"Pacing_Report_{ch_range}.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def run(self, task: str, run_dir: Path) -> str:
        return "PacingDoctor: 请通过 check_batch_pacing() 方法直接调用"
