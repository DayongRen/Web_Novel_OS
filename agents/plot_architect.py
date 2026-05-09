"""
Plot Architect Agent — 剧情架构师
生成总纲、分卷纲、前30章详细章纲，维护主线/支线/反派线。
"""

from pathlib import Path

from .base_agent import BaseAgent


class PlotArchitectAgent(BaseAgent):

    role = "Plot Architect（剧情架构师）"
    system_prompt = """
你是剧情架构师，专注于构建可持续连载的故事骨架。

你的职责：
1. 生成全书总纲（核心矛盾、主线走向、结局方向）
2. 生成分卷纲（每卷目标、卷反派、卷爽点、卷钩子）
3. 生成章节功能表（每章有明确存在理由）
4. 维护主线、支线、反派线的节奏协调
5. 确保每30章有一次主线推进
6. 确保开头30章节奏紧凑，不拖沓

原则：
- 每章必须有功能（推进剧情/升级冲突/释放爽点/埋设伏笔）
- 支线不能超过主线重量
- 反派必须有完整动机和弧线
- 大纲只是骨架，留给写作时的弹性空间
"""

    def generate_full_outline(self, run_dir: Path) -> str:
        context = self._build_base_context()
        genre_tpl = self._load_genre_template()
        beat_sheet = self._load_beat_sheet()
        word_count = self.config.get("project", {}).get("target_word_count", 300000)
        chapter_count = self.config.get("project", {}).get("target_chapter_count", 150)

        prompt = f"""
{context}

{genre_tpl}

{beat_sheet}

## 任务：生成全书总纲

目标字数：{word_count} 字
目标章数：{chapter_count} 章

请生成完整的全书总纲，包含：

### 一、核心矛盾
主角的根本欲望与最大阻碍是什么？

### 二、全书主线
分5-6个阶段描述主线走向，每个阶段包含：
- 阶段目标
- 核心冲突
- 主角状态
- 阶段爽点

### 三、分卷规划
每卷包含：
- 卷名
- 章节范围
- 卷目标（读者层面：这卷给读者什么？）
- 卷反派/主要对立力量
- 卷核心爽点（至少2个）
- 卷主要谜团（至少1个）
- 卷结尾大钩子（引向下卷的关键悬念）
- 主角成长体现

### 四、主要人物线
- 主角弧（全书）
- 第一女主/重要伴侣线
- 主反派线
- 重要配角线（各1-2句话）

### 五、核心伏笔规划
列出5-8条必须前期埋下、后期回收的重要伏笔。

### 六、结局方向
结局类型和情绪基调。

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Full_Outline.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/outlines/03_full_outline.md"
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        repo_path.write_text(result, encoding="utf-8")
        return result

    def generate_volume_outlines(self, run_dir: Path) -> str:
        context = self._build_base_context()
        genre_tpl = self._load_genre_template()

        prompt = f"""
{context}

{genre_tpl}

## 任务：生成分卷详细纲要

基于已有的全书总纲，为每一卷生成详细纲要。

每卷纲要包含：

### 卷X：[卷名]（第X-X章，约X万字）

**卷级目标**
读者视角：这卷结束后，读者得到了什么？

**主要情节线**
1. 主线（A线）：5-8个主要情节节点
2. 感情线（B线，如有）：3-5个推进节点
3. 配角/支线（C线）：2-3个节点

**卷内节奏设计**
- 小爽点分布（标注章节）
- 中爽点位置
- 大爽点（卷高潮）位置
- 信息揭露节点

**卷反派设计**
- 名字/身份
- 动机
- 行动逻辑
- 最终命运

**卷核心谜团**
- 谜团内容
- 预计揭露章节

**卷结尾大钩子**
（一定要让读者停不下来，引入下卷）

**新增设定**
（此卷新增的世界观/设定要点）

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Volume_Outlines.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/outlines/04_volume_outlines.md"
        repo_path.write_text(result, encoding="utf-8")
        return result

    def generate_chapter_outlines(self, start_ch: int, end_ch: int, run_dir: Path) -> str:
        context = self._build_base_context()
        genre_tpl = self._load_genre_template()
        pacing = self.config.get("pacing", {})

        prompt = f"""
{context}

{genre_tpl}

## 节奏要求
{pacing}

## 任务：生成第{start_ch}-{end_ch}章详细章纲

为每一章生成详细章纲卡片，格式如下：

---
**第X章：[章节标题]**

- **章节功能**：[推进主线/升级冲突/释放爽点/埋设伏笔/人物塑造]
- **目标字数**：约XXXX字
- **场景**：
  1. 场景一：地点——目标——冲突——转折
  2. 场景二：...
- **本章冲突**：核心冲突一句话描述
- **读者收益**：读者看完本章得到什么（爽点/信息/情绪）
- **结尾钩子**：最后一句话要让读者翻下一章
- **伏笔**：（本章埋下或推进的伏笔）
- **承诺变动**：（新开承诺/关闭承诺）
- **设定更新**：（新增人物/地点/道具等）

---

每章都要有明确的"存在理由"。如果一章只有闲聊、赶路、训练，必须加入冲突或信息揭露。

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / f"Chapter_Outlines_{start_ch:03d}_{end_ch:03d}.md"
        out_path.write_text(result, encoding="utf-8")

        repo_path = self.project_root / "project_repo/outlines/05_chapter_outlines.md"
        existing = ""
        if repo_path.exists():
            existing = repo_path.read_text(encoding="utf-8")
        repo_path.write_text(existing + "\n\n" + result, encoding="utf-8")
        return result

    def generate_ending_plan(self, run_dir: Path) -> str:
        context = self._build_base_context()

        prompt = f"""
{context}

## 任务：生成结局规划

请生成完整的结局规划文档，包含：

### 1. 结局类型
选择并说明理由：HE（完美结局）/ BE（悲剧结局）/ OE（开放结局）

### 2. 主线终点
主角的核心目标如何实现（或以何种方式未实现）？

### 3. 所有主要承诺回收计划
列出全书所有主要承诺，标注预计回收章节。

### 4. 情感高潮设计
结局最重要的情感时刻是什么？

### 5. 反派结局
主反派的最终命运和原因。

### 6. 配角结局
每个重要配角的结局一句话说明。

### 7. 伏笔回收清单
所有前期埋下的伏笔如何在结局段回收。

### 8. 结局节奏
最后X章的节奏设计（几章高潮，几章收束）。

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Ending_Plan.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/outlines/06_ending_plan.md"
        repo_path.write_text(result, encoding="utf-8")
        return result

    def run(self, task: str, run_dir: Path) -> str:
        if task == "full_outline":
            return self.generate_full_outline(run_dir)
        elif task == "volume_outlines":
            return self.generate_volume_outlines(run_dir)
        elif task == "ending_plan":
            return self.generate_ending_plan(run_dir)
        elif task.startswith("chapters_"):
            parts = task.split("_")
            start_ch = int(parts[1])
            end_ch = int(parts[2])
            return self.generate_chapter_outlines(start_ch, end_ch, run_dir)
        return self.generate_full_outline(run_dir)
