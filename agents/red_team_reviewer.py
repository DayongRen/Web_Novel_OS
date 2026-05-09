"""
Red Team Reviewer Agent — 毒舌读者/编辑
站在读者和编辑角度找弃书点、套路疲劳、主角不讨喜等问题。
"""

from pathlib import Path

from .base_agent import BaseAgent


class RedTeamReviewerAgent(BaseAgent):

    role = "Red Team Reviewer（毒舌读者/编辑）"
    system_prompt = """
你是毒舌读者兼资深网文编辑，你的任务就是找问题。

你的职责：
1. 找出读者最可能弃书的位置和原因
2. 指出套路疲劳（重复使用相同套路）
3. 指出主角不讨喜的地方
4. 指出爽点不足或爽点失效
5. 指出感情线尴尬
6. 指出设定漏洞会被读者注意到的部分

你的立场：
- 你代表最苛刻的类型读者
- 你不会为了礼貌而粉饰太平
- 你的每个批评都要有具体依据
- 你的每个批评后面必须跟着修复方案

每次审核都要问：
1. 读者最可能在哪一章弃书？
2. 为什么？
3. 怎么修？
"""

    def review_concept(self, run_dir: Path) -> str:
        context = self._build_base_context()
        genre_tpl = self._load_genre_template()

        prompt = f"""
{context}

{genre_tpl}

## 任务：概念阶段红队审查

作为一个刁钻的类型读者，对这个项目的概念阶段进行审查：

### 1. 核心创意的市场风险
这个创意有什么先天不足？读者会对哪些设定抵触？

### 2. 类型承诺是否清晰
这个故事的类型是什么？读者知道自己会得到什么吗？

### 3. 主角吸引力评估
这个主角会让目标读者产生认同感吗？有哪些问题？

### 4. 最大潜在弃书点（按章节预测）
根据目前大纲，预测最可能的弃书章节：
- 最危险的章节区间
- 原因
- 预防措施

### 5. 市场差异化
这本书和同类书有什么不同？如果没有明显差异，为什么读者要选它？

### 6. 一票否决风险
有没有任何单一元素可能直接毁掉这本书（一旦出现就大量弃书）？

### 综合评级：S/A/B/C/D（市场竞争力）
说明评级理由。

输出为 Markdown，中文。语气直接，不客套。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "RedTeam_Concept_Review.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def review_chapters(self, chapters_content: str, chapter_range: str, run_dir: Path) -> str:
        prompt = f"""
## 章节内容（{chapter_range}）
{chapters_content}

## 任务：章节红队审查

作为苛刻读者，对这批章节进行无情审查：

### 1. 最危险的弃书点
本批次中读者最可能停下不读的地方（具体到章节内的哪个段落）。

### 2. 主角形象问题
本批次中主角有没有让人讨厌或无聊的表现？

### 3. 节奏问题
哪里最拖沓？哪里最无聊？

### 4. 套路疲劳
有没有重复出现让人看腻的套路？

### 5. 逻辑漏洞
读者会发现的逻辑问题（不一定需要硬核论证，只要"感觉不对"就算）。

### 6. 爽点失效
有没有本来应该爽但实际上不爽的场景？原因是什么？

### 7. 下批次最需要修复的3件事
按优先级排序，每条都要有具体建议。

输出为 Markdown，中文。语气直接，不客套。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / f"RedTeam_Chapters_{chapter_range}.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def run(self, task: str, run_dir: Path) -> str:
        if task == "concept":
            return self.review_concept(run_dir)
        return self.review_concept(run_dir)
