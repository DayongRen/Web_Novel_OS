"""
Commercial Hook Agent — 商业钩子代理
优化书名、简介、前三章、章节标题、卖点标签。
"""

from pathlib import Path

from .base_agent import BaseAgent


class CommercialHookAgent(BaseAgent):

    role = "Commercial Hook Agent（商业钩子代理）"
    system_prompt = """
你是商业钩子代理，专注于小说的市场入口优化。

你的职责：
1. 生成多个有竞争力的书名候选
2. 优化小说简介（封面简介+内文简介）
3. 分析前三章是否有足够的钩子
4. 优化章节标题
5. 生成市场标签策略

原则：
- 书名要让读者一眼看出类型和卖点
- 简介的第一句话决定点击率
- 前三章是读者决定是否继续读的关键窗口
- 标签要精准匹配平台推荐算法
"""

    def generate_concept_package(self, run_dir: Path) -> str:
        context = self._build_base_context()
        genre_tpl = self._load_genre_template()
        target_reader = self.config.get("reader", {}).get("target_reader", "")
        platform = self.config.get("project", {}).get("target_platform", "")

        prompt = f"""
{context}

{genre_tpl}

## 目标读者：{target_reader}
## 目标平台：{platform}

## 任务：生成商业概念包

### 一、书名候选（10个）
对每个书名说明：
- 书名本身
- 吸引点（这个名字抓住了什么读者心理）
- 适合平台（哪个平台投放效果最好）
- 风险（可能的问题）

### 二、一句话简介（5个版本）
每个版本不超过30字，要有强烈的钩子感。

### 三、封面简介（300-500字）
- 第一段：抓住读者（最强钩子）
- 第二段：建立场景和角色
- 第三段：核心冲突
- 最后：一句让人点击的结尾

### 四、内文简介（100字以内的超短版）
用于手机端展示。

### 五、标签策略
- 必选标签（精准匹配类型）
- 差异化标签（区分同类书的独特标签）
- 流量标签（高搜索量标签）
- 避免标签（会引来错误读者的标签）

### 六、竞品分析
这类书在市场上的竞争情况（不提具体书名，只说类型格局）。

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Concept_Package.md"
        out_path.write_text(result, encoding="utf-8")

        for label, repo_file in [
            ("书名候选", "project_repo/market/Title_Candidates.md"),
            ("简介", "project_repo/market/Synopsis.md"),
            ("卖点", "project_repo/market/Selling_Points.md"),
        ]:
            pass

        return result

    def generate_logline(self, run_dir: Path) -> str:
        context = self._build_base_context()

        prompt = f"""
{context}

## 任务：生成 Logline 和核心卖点

### 一、Logline（不超过50字）
一句话说清楚：谁（主角）+ 处境 + 目标 + 最大障碍 + 核心吸引力

### 二、Elevator Pitch（100字以内）
如果你向一个陌生人推荐这本书，你会怎么说？

### 三、核心卖点（5-7条）
每条卖点：
- 卖点描述
- 对应读者需求
- 在书中的体现章节

### 四、情感钩子
这本书能给读者哪种核心情感体验？

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Logline.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/outlines/01_logline.md"
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        repo_path.write_text(result, encoding="utf-8")
        return result

    def analyze_opening_hook(self, run_dir: Path) -> str:
        context = self._build_base_context()
        ch1 = self.read_file("project_repo/manuscript/volume_001/ch001.md")
        ch2 = self.read_file("project_repo/manuscript/volume_001/ch002.md")
        ch3 = self.read_file("project_repo/manuscript/volume_001/ch003.md")

        prompt = f"""
{context}

## 前三章内容

### 第1章
{ch1}

### 第2章
{ch2}

### 第3章
{ch3}

## 任务：前三章钩子分析报告

### 1. 第一段钩子
读者读第一段会不会继续读？评级+理由。

### 2. 第一章末钩子
读完第一章会不会翻第二章？评级+理由。

### 3. 类型承诺建立
前三章是否清晰建立了类型承诺？读者知道这是什么类型的书吗？

### 4. 主角吸引力
读者会喜欢/同情/为主角揪心吗？哪些地方建立了情感连接？

### 5. 冲突建立
前三章的核心冲突是否清晰？

### 6. 弃书风险点
在哪个位置读者最可能放弃？为什么？

### 7. 修改建议
如果只能改一件事，改什么效果最大？

### 总体开篇评级：A/B/C/D

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Opening_Hook_Report.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def generate_synopsis(self, run_dir: Path) -> str:
        context = self._build_base_context()

        prompt = f"""
{context}

## 任务：生成最终简介

基于已完成的内容，生成面向读者的正式简介：

### 一、封面简介（500字以内）
用来吸引读者点击的正式简介。

### 二、追更简介（200字）
已追更读者看到的版本，可以有更多剧透。

### 三、编辑推荐语（50字以内）
平台编辑推荐位会用的一句话。

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Final_Synopsis.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/market/Synopsis.md"
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        repo_path.write_text(result, encoding="utf-8")
        return result

    def run(self, task: str, run_dir: Path) -> str:
        if task == "concept":
            return self.generate_concept_package(run_dir)
        elif task == "logline":
            return self.generate_logline(run_dir)
        elif task == "opening_hook":
            return self.analyze_opening_hook(run_dir)
        elif task == "synopsis":
            return self.generate_synopsis(run_dir)
        return self.generate_concept_package(run_dir)
