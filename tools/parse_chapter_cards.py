"""
tools/parse_chapter_cards.py — 从 PlotArchitect 的章纲 Markdown 提取结构化 ChapterCard

LLM 生成的章纲是自然语言 Markdown，本工具请 LLM 将其结构化为 ChapterCard YAML，
然后存入 project_repo/outlines/chapter_cards.yaml。

使用：
  python -m tools.parse_chapter_cards [project_root]
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent

CARD_TEMPLATE = """---
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
"""


def parse_cards_with_llm(project_root: Path, force: bool = False) -> str:
    """调用 LLM 将章纲 Markdown 转换为 ChapterCard YAML。"""
    from agents import PlotArchitectAgent
    import yaml as _yaml

    config_path = project_root / "novel_config.yaml"
    if not config_path.exists():
        return "❌ novel_config.yaml 不存在"

    with open(config_path, encoding="utf-8") as f:
        config = _yaml.safe_load(f) or {}

    outlines_path = project_root / "project_repo/outlines/05_chapter_outlines.md"
    if not outlines_path.exists():
        return "❌ chapter_outlines.md 不存在，请先运行 outline 阶段"

    card_path = project_root / "project_repo/outlines/chapter_cards.yaml"
    if card_path.exists() and not force:
        from schemas.chapter_card_schema import ChapterCardIndex
        idx = ChapterCardIndex(card_path)
        return f"ℹ️  chapter_cards.yaml 已存在 ({len(idx.cards)} 张卡)。使用 --force 强制重新生成。"

    outline_text = outlines_path.read_text(encoding="utf-8")

    from agents.base_agent import BaseAgent
    from llm import make_client

    agent = BaseAgent(config, project_root)

    prompt = f"""
以下是章节大纲文本：

{outline_text[:6000]}

请将每一章的信息提取为结构化 YAML ChapterCard，输出格式如下：

```yaml
chapters:
  - chapter: 1
    title: "章节标题"
    word_target: 2000
    chapter_function:
      - "推进主线"
    pov: "第三人称有限视角（主角）"
    scene_list:
      - scene_id: "S1.1"
        location: "地点"
        goal: "目标"
        conflict: "冲突"
        turn: "转折"
    reader_payoff:
      - "读者收益"
    foreshadowing:
      - "伏笔"
    ending_hook: "结尾钩子"
    canon_updates:
      - "设定更新"
    promise_opens: []
    promise_closes: []
```

严格要求：
1. 每章一个 ChapterCard
2. 所有字段必须填写，没有信息时写空字符串或空列表
3. 只输出 YAML，不要任何说明文字
"""
    result = agent.call_llm(prompt)

    yaml_content = result.strip()
    for fence in ("```yaml", "```yml", "```"):
        if yaml_content.startswith(fence):
            yaml_content = yaml_content[len(fence):]
    if yaml_content.endswith("```"):
        yaml_content = yaml_content[:-3]
    yaml_content = yaml_content.strip()

    try:
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict) or "chapters" not in data:
            return f"❌ LLM 输出不符合预期格式:\n{yaml_content[:300]}"

        card_path.parent.mkdir(parents=True, exist_ok=True)
        with open(card_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return f"✅ 已生成 {len(data['chapters'])} 张 ChapterCard → {card_path}"
    except yaml.YAMLError as e:
        return f"❌ YAML 解析失败: {e}\n原始输出:\n{yaml_content[:500]}"


def check_card_coverage(project_root: Path, start: int, end: int) -> tuple[bool, str]:
    """检查指定章节范围是否都有 ChapterCard，返回 (ok, message)。"""
    from schemas.chapter_card_schema import ChapterCardIndex

    card_path = project_root / "project_repo/outlines/chapter_cards.yaml"
    if not card_path.exists():
        return False, f"❌ chapter_cards.yaml 不存在，无法写章节 {start}-{end}"

    idx = ChapterCardIndex(card_path)
    missing = idx.missing_for_range(start, end)
    if missing:
        return False, f"❌ 章节 {missing} 缺少 ChapterCard，请先生成章纲或手动补充"
    return True, f"✅ 第{start}-{end}章 ChapterCard 完整"


if __name__ == "__main__":
    force = "--force" in sys.argv
    root = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else ROOT
    print(parse_cards_with_llm(root, force=force))
