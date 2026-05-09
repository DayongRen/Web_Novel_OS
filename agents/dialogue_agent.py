"""
Dialogue Agent — 对话专员
优化人物对白，区分角色说话风格，增加潜台词和冲突。
"""

from pathlib import Path

from .base_agent import BaseAgent


class DialogueAgent(BaseAgent):

    role = "Dialogue Agent（对话专员）"
    system_prompt = """
你是对话专员，专注于让人物对白更鲜活、更有层次。

你的职责：
1. 优化章节中的对话质量
2. 确保每个角色有独特的说话方式
3. 减少"说明书式对话"（只为传递信息）
4. 增加潜台词（人物话里有话）
5. 让对话同时推进情节、揭示人物、制造冲突

原则：
- 好的对话说的是A，意思是B
- 每句对话都应该有目的（推剧情/揭性格/制造张力）
- 不同角色不能说话方式一模一样
- 冲突对话不应该是互骂，而是各自坚持不同立场
"""

    def polish_dialogue(self, chapter_content: str, chapter_num: int, run_dir: Path) -> str:
        context = self._build_base_context()
        char_bible = self.read_file("project_repo/canon/Character_Bible.md")
        dialogue_guide = self.read_file("project_repo/style/Dialogue_Guide.md")

        prompt = f"""
## 人物设定（声音特征）
{char_bible}

## 对话风格指南
{dialogue_guide}

## 第{chapter_num}章原文
{chapter_content}

## 任务：对话优化

请对本章所有对话进行优化，要求：

1. **声音区分**：每个角色的说话方式要有明显区别
2. **潜台词增加**：至少找出3处可以增加潜台词的对话
3. **说明书对话消除**：找出纯粹在传递信息的对话，改写为角色行为
4. **冲突对话升级**：让争执更有层次感

输出格式：
- 首先列出"问题对话清单"（标出行号或对话内容）
- 然后对每处问题对话给出修改版本
- 最后给出整体对话质量评级（A/B/C/D）和改进建议

输出为 Markdown，中文。
"""
        result = self.call_llm(prompt)
        out_path = run_dir / f"Dialogue_Polish_Ch{chapter_num:03d}.md"
        out_path.write_text(result, encoding="utf-8")
        return result

    def run(self, task: str, run_dir: Path) -> str:
        return "DialogueAgent: 请通过 polish_dialogue() 方法直接调用"
