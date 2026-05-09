"""
Character Keeper Agent — 人物管理员
维护人设一致性，追踪人物弧线，防止角色降智和工具人化。
"""

from pathlib import Path

from .base_agent import BaseAgent


class CharacterKeeperAgent(BaseAgent):

    role = "Character Keeper（人物管理员）"
    system_prompt = """
你是人物管理员，负责所有角色的生命质量。

你的职责：
1. 建立和维护 Character_Bible.md
2. 追踪每个角色的动机、弧线、行为一致性
3. 防止角色降智（为推剧情而变蠢）
4. 防止配角工具人化（只为服务主角存在）
5. 检查角色行为是否符合其已建立的性格和动机
6. 追踪角色关系的发展与变化

原则：
- 每个出场超过3次的角色都需要独立动机
- 反派必须相信自己是正确的
- 角色犯错要有人性逻辑，不能是为了方便剧情
- 人物成长必须有痕迹，不能突然转变
"""

    def build_character_bible(self, run_dir: Path) -> str:
        context = self._build_base_context()
        genre_tpl = self._load_genre_template()

        prompt = f"""
{context}

{genre_tpl}

## 任务：构建人物圣经（Character Bible）

基于故事圣经和类型模板，为所有主要人物建立详细档案。

格式如下：

---
## [人物名]

**基本信息**
- 年龄/外貌：
- 身份/职业：
- 出场章节：

**核心动机**
（这个人物最根本想要什么？为了什么而行动？）

**性格核心**
三个最核心的性格特征，每条用一个具体场景举例说明。

**弱点与阴暗面**
（没有弱点的角色是纸板人）

**行为原则**
这个角色绝对不会做的3件事。
这个角色在压力下会做的3件事。

**声音特征**
这个角色说话的风格特征（用词习惯、口头禅、说话节奏）。

**人物弧线**
- 起点状态：
- 中点转变：
- 终点状态：

**与主角的关系**
关系类型和发展轨迹。

**功能定位**
在故事中承担的叙事功能。

---

必须涵盖：主角、第一女主（如有）、主反派、最重要的2-3个配角。

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Character_Bible.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/canon/Character_Bible.md"
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        repo_path.write_text(result, encoding="utf-8")
        return result

    def check_consistency(self, chapter_content: str, chapter_num: int, run_dir: Path) -> str:
        context = self._build_base_context()

        prompt = f"""
{context}

## 待检查的章节内容（第{chapter_num}章）
{chapter_content}

## 任务：人物一致性检查

请检查本章中每个出现的角色是否符合其在 Character Bible 中建立的设定：

### 检查维度
1. **动机一致性**：角色的行为是否符合其已建立的动机？
2. **性格一致性**：对话和行为是否符合其性格特征？
3. **知识一致性**：角色是否知道不该知道的事？
4. **弧线进展**：角色在本章的成长是否合理？
5. **声音一致性**：对白风格是否符合角色声音特征？

### 输出格式
对每个出场角色：
- 角色名：[评级 PASS/WARN/FAIL]
- 问题描述（如有）：
- 修改建议（如有）：

### 综合评级
- 整体人物一致性：[PASS/WARN/FAIL]
- 最严重问题（如有）：
- 优先修改项：

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / f"Character_Check_Ch{chapter_num:03d}.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def update_arc_tracker(self, batch_summary: str, run_dir: Path) -> str:
        existing = self.read_file("project_repo/continuity/Character_Arc_Tracker.yaml")
        context = self._build_base_context()

        prompt = f"""
{context}

## 当前人物弧追踪
```yaml
{existing}
```

## 本批次摘要
{batch_summary}

## 任务：更新人物弧追踪

基于本批次内容，更新 Character_Arc_Tracker，输出完整的 YAML 格式：

格式：
```yaml
characters:
  - name: 角色名
    arc_stage: 当前弧线阶段（opening/development/crisis/transformation/resolution）
    current_state: 一句话描述当前状态
    recent_changes: 本批次发生的变化
    pending_arc_beats:
      - 尚未完成的弧线节点
    last_updated_chapter: 最后出现章节
```

只输出 YAML 内容。
"""
        result = self.call_llm(prompt)
        yaml_content = result.strip()
        if yaml_content.startswith("```yaml"):
            yaml_content = yaml_content[7:]
        if yaml_content.endswith("```"):
            yaml_content = yaml_content[:-3]
        yaml_content = yaml_content.strip()

        repo_path = self.project_root / "project_repo/continuity/Character_Arc_Tracker.yaml"
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        repo_path.write_text(yaml_content, encoding="utf-8")
        return yaml_content

    def run(self, task: str, run_dir: Path) -> str:
        if task == "build_bible":
            return self.build_character_bible(run_dir)
        elif task == "update_arcs":
            return self.update_arc_tracker("", run_dir)
        return self.build_character_bible(run_dir)
