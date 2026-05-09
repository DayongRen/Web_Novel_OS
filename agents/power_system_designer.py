"""
Power System Designer Agent — 力量体系设计师
设计升级/修炼/异能/战斗体系，保证等级可见、代价清晰、不随意开挂。
"""

from pathlib import Path

from .base_agent import BaseAgent


class PowerSystemDesignerAgent(BaseAgent):

    role = "Power System Designer（力量体系设计师）"
    system_prompt = """
你是力量体系设计师，专门为奇幻、仙侠、异能、无限流、科幻等类型设计战力体系。

你的职责：
1. 设计清晰的等级体系
2. 设定升级所需资源和代价
3. 设定战力边界（什么情况下无敌，什么情况下有弱点）
4. 设计力量体系的美感和视觉感
5. 防止无成本开挂

原则：
- 等级要可见（读者能感受到差距）
- 升级要有代价（时间/资源/牺牲）
- 战力要有边界（无敌的前提条件）
- 隐藏天赋要有前期暗示
- 力量体系要服务故事，不要本末倒置
"""

    def design_power_system(self, run_dir: Path) -> str:
        context = self._build_base_context()
        genre_tpl = self._load_genre_template()

        prompt = f"""
{context}

{genre_tpl}

## 任务：设计力量体系（Power System）

请为本故事设计完整的力量体系文档：

### 一、体系概述
- 力量来源（修炼/变异/科技/天赋/契约等）
- 体系名称
- 核心逻辑

### 二、等级划分
为每个等级设计：
- 等级名称
- 能力描述（普通读者能理解的具体表现）
- 达到该等级的条件/代价
- 主角预计到达该等级的时间节点（第X章左右）

（至少设计8-12个等级，留足成长空间）

### 三、突破机制
- 突破需要什么（资源/感悟/机遇/战斗）
- 突破失败的风险
- 突破成功的代价

### 四、特殊能力/天赋
- 主角的特殊天赋（必须有代价或限制）
- 天赋的前期暗示方式
- 天赋的成长方向

### 五、战斗规则
- 跨级挑战是否可能（条件是什么）
- 群体战的处理逻辑
- 特殊环境对战力的影响

### 六、资源体系
- 主要修炼资源（名称+功效+稀缺程度）
- 资源获取途径
- 资源经济逻辑

### 七、体系禁区
（在这个力量体系中，什么是绝对不可能的？）

### 八、开挂防护
列出5条防止主角无成本开挂的设定约束。

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / "Power_System.md"
        out_path.write_text(result, encoding="utf-8")
        repo_path = self.project_root / "project_repo/canon/Power_System.md"
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        repo_path.write_text(result, encoding="utf-8")
        return result

    def run(self, task: str, run_dir: Path) -> str:
        return self.design_power_system(run_dir)
