"""
Genre Strategist Agent — 类型策略师
根据项目配置选择类型范本、节奏模板，输出完整的类型策略报告。
"""

from pathlib import Path

import yaml

from .base_agent import BaseAgent


class GenreStrategistAgent(BaseAgent):

    role = "Genre Strategist（类型策略师）"
    system_prompt = """
你是类型策略师，精通中国网络文学所有主流类型的市场规律和读者期待。

你的职责：
1. 分析用户创意并识别所属类型
2. 匹配最合适的类型范本（genre_profile）
3. 根据目标字数选择节奏模板（beat_sheet）
4. 根据目标平台调整写作参数
5. 明确指出类型的核心承诺（不可违背的读者期待）
6. 列出类型的禁区（这样写会直接劝退读者）

类型范本只提供结构参考，不允许抄袭具体情节。
"""

    def analyze_genre(self, run_dir: Path) -> str:
        context = self._build_base_context()
        genre = self.config.get("genre", {}).get("primary", "unknown")
        genre_tpl = self._load_genre_template()
        beat_sheet = self._load_beat_sheet()
        platform = self.config.get("project", {}).get("target_platform", "general_webnovel")
        word_count = self.config.get("project", {}).get("target_word_count", 300000)

        prompt = f"""
{context}

{genre_tpl}

{beat_sheet}

## 任务：类型匹配与策略分析

基于以上信息，请生成完整的类型策略报告：

### 1. 类型识别
- 主类型：{genre}
- 子类型/混合类型
- 最相近的标杆作品类型（不列具体书名，只说类型特征）

### 2. 核心承诺（读者购买这类书的理由）
列出5-7个类型核心承诺，每条都要说明：
- 承诺内容
- 第一次兑现的最晚章节
- 失败代价

### 3. 节奏规划
基于目标字数 {word_count} 字，给出：
- 小爽点间隔：每X章一次
- 中爽点间隔：每X章一次
- 大爽点间隔：每X章一次
- 悬念钩子频率

### 4. 平台适配（{platform}）
- 章节长度建议
- 开篇节奏建议
- 禁忌内容

### 5. 类型禁区（绝对不能做的事）
列出7-10条，每条说明会导致什么后果。

### 6. 前10章必做清单
逐条列出前10章必须完成的类型任务。

### 7. 类型成功公式
一句话总结这类书成功的核心要素。

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Genre_Match_Report.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def parse_user_idea(self, run_dir: Path) -> str:
        core_idea = self.read_file("project_repo/outlines/00_core_idea.md")
        genre_tpl = self._load_genre_template()

        prompt = f"""
## 用户原始创意
{core_idea}

{genre_tpl}

## 任务：创意解析与扩展

请将用户的原始创意解析为结构化信息：

### 1. 核心元素提取
- 主角：（背景、起点、欲望）
- 反派/对立力量：
- 核心冲突：
- 世界设定：
- 类型标签：

### 2. 卖点识别
列出3-5个最有市场价值的卖点。

### 3. 创意扩展建议
基于类型惯例，补充以下内容：
- 建议增加的核心冲突（当前创意可能缺少的）
- 建议增加的关键人物角色
- 建议增加的情绪钩子

### 4. 风险预警
创意中存在的潜在问题（类型不符、读者接受度风险等）。

### 5. 结构化创意摘要（供后续 Agent 使用）
用YAML格式输出核心要素。

输出格式：Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "User_Idea_Parsed.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def run(self, task: str, run_dir: Path) -> str:
        if task == "parse_idea":
            return self.parse_user_idea(run_dir)
        return self.analyze_genre(run_dir)
