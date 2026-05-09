"""
Worldbuilding Keeper Agent — 世界观管理员
维护世界规则，防止设定冲突，管理所有正典信息。
"""

from pathlib import Path

from .base_agent import BaseAgent


class WorldbuildingKeeperAgent(BaseAgent):

    role = "Worldbuilding Keeper（世界观管理员）"
    system_prompt = """
你是世界观管理员，是故事世界的守护者和档案管理员。

你的职责：
1. 构建并维护 World_Bible.md
2. 管理 Location_Ledger、Item_Ledger、Faction_Map、Timeline
3. 确保所有设定内部自洽
4. 防止世界规则被随意修改
5. 记录每一个新出现的世界要素

原则：
- 世界有规则，规则有成本
- 新增设定必须与已有设定兼容
- 设定服务于故事，不是为了炫耀
- 地理、时间、资源都需要逻辑自洽
"""

    def build_world_bible(self, run_dir: Path) -> str:
        context = self._build_base_context()
        genre_tpl = self._load_genre_template()

        prompt = f"""
{context}

{genre_tpl}

## 任务：构建世界观圣经（World Bible）

基于核心创意和类型范本，建立完整的世界观文档。

### 一、世界基础设定
- 世界类型（现代都市/古代东方/架空大陆/星际文明等）
- 时代背景
- 世界核心规则（最重要的3-5条世界运行法则）

### 二、地理与空间
主要地点列表（每个地点：名称、简描、在故事中的功能）

### 三、社会结构
- 权力体系（谁在统治，怎么统治）
- 阶层划分
- 重要机构/组织

### 四、历史与神话
- 对故事有影响的关键历史事件
- 传说或神话（如有，限3条以内）

### 五、经济与资源
- 关键资源是什么
- 经济逻辑简述

### 六、文化与习俗
对故事有影响的文化要素（限5条）

### 七、世界禁区
（在这个世界中，什么是绝对做不到的？什么是至高禁忌？）

输出为 Markdown，中文。详细但不冗余。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "World_Bible.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/canon/World_Bible.md"
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        repo_path.write_text(result, encoding="utf-8")
        return result

    def build_faction_map(self, run_dir: Path) -> str:
        context = self._build_base_context()

        prompt = f"""
{context}

## 任务：生成势力地图（Faction Map）

为故事中所有主要势力建立档案：

每个势力包含：
- **势力名称**
- **类型**：（政治/军事/商业/宗教/地下/学术等）
- **规模**：（人数/影响范围）
- **领袖**：（名字及简介）
- **核心目标**：（这个势力最根本想要什么）
- **行动逻辑**：（他们如何追求目标）
- **与主角的关系**：（敌/友/中立/复杂）
- **与其他势力的关系**：（简要说明）
- **内部矛盾**：（势力内部的分歧，让势力立体化）
- **衰落/被消灭的可能方式**：（伏笔）

所有势力之间的关系矩阵（简表）。

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Faction_Map.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/canon/Faction_Map.md"
        repo_path.write_text(result, encoding="utf-8")
        return result

    def build_timeline(self, run_dir: Path) -> str:
        context = self._build_base_context()

        prompt = f"""
{context}

## 任务：生成时间线（Timeline）

建立故事的时间线文档：

### 一、故事前史（背景事件）
对故事有影响的历史事件，时间倒序排列。

### 二、故事开始前（主角视角）
主角生活中的关键时间节点。

### 三、故事内时间线
以章节为锚点，记录故事内时间流逝：
格式：第X章 | 故事时间（如：故事第3天） | 关键事件

### 四、时间线约束
（列出时间上的重要约束，如：某事件必须在X之前发生）

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Timeline.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/canon/Timeline.md"
        repo_path.write_text(result, encoding="utf-8")
        return result

    def build_relationship_map(self, run_dir: Path) -> str:
        context = self._build_base_context()

        prompt = f"""
{context}

## 任务：生成关系图（Relationship Map）

### 一、主角关系网
以主角为中心，列出所有重要关系：
- 关系对象
- 关系性质（家人/朋友/导师/对手/爱人/竞争者/恩人/仇人）
- 关系起点
- 关系走向（会如何发展）
- 关键转折点

### 二、重要人物关系矩阵
列出5-8个重要人物之间的关系（简表格式）。

### 三、潜在关系变化
哪些关系会在故事中发生根本性转变？

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Relationship_Map.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/canon/Relationship_Map.md"
        repo_path.write_text(result, encoding="utf-8")
        return result

    def run(self, task: str, run_dir: Path) -> str:
        if task == "world_bible":
            return self.build_world_bible(run_dir)
        elif task == "faction_map":
            return self.build_faction_map(run_dir)
        elif task == "timeline":
            return self.build_timeline(run_dir)
        elif task == "relationship_map":
            return self.build_relationship_map(run_dir)
        return self.build_world_bible(run_dir)
