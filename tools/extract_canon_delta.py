"""
tools/extract_canon_delta.py — Canon Delta 提取器

每章写完后，自动提取章节中出现的新增人物/地点/道具/设定，
生成 Canon_Update_Request.yaml，并可自动追加到对应的 canon 文件。

使用：
  python -m tools.extract_canon_delta [project_root] [chapter_num]
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).parent.parent

CANON_FILES = {
    "characters": "project_repo/canon/Character_Bible.md",
    "locations": "project_repo/canon/Location_Ledger.md",
    "items": "project_repo/canon/Item_Ledger.md",
    "factions": "project_repo/canon/Faction_Map.md",
    "power_abilities": "project_repo/canon/Power_System.md",
    "timeline_events": "project_repo/canon/Timeline.md",
}


def extract_delta_with_llm(project_root: Path, chapter_num: int, chapter_content: str) -> dict:
    """让 LLM 提取章节中的新增设定元素。"""
    import yaml as _yaml

    config_path = project_root / "novel_config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        config = _yaml.safe_load(f) or {}

    from agents.base_agent import BaseAgent
    agent = BaseAgent(config, project_root)

    existing_chars = ""
    char_path = project_root / "project_repo/canon/Character_Bible.md"
    if char_path.exists():
        existing_chars = char_path.read_text(encoding="utf-8")[:1000]

    existing_locs = ""
    loc_path = project_root / "project_repo/canon/Location_Ledger.md"
    if loc_path.exists():
        existing_locs = loc_path.read_text(encoding="utf-8")[:500]

    prompt = f"""
## 第{chapter_num}章内容
{chapter_content}

## 已登记人物（节选）
{existing_chars}

## 已登记地点（节选）
{existing_locs}

## 任务：提取新增设定元素

请识别本章中首次出现的（或有重要新信息的）：
1. 新人物（名字/身份/外貌/性格特征）
2. 新地点（名称/类型/描述）
3. 新道具/重要物品（名称/功能/归属）
4. 新势力/组织（名称/类型）
5. 新时间线事件（故事内时间/事件）
6. 新能力/技能（名称/效果，如有）

只提取**首次出现**或**有实质新信息**的元素，不要重复已知信息。

输出格式（YAML，如某类为空则写 []）：
```yaml
chapter: {chapter_num}
new_characters:
  - name: ""
    identity: ""
    first_appearance: {chapter_num}
    key_traits: ""
new_locations:
  - name: ""
    type: ""
    description: ""
    first_appearance: {chapter_num}
new_items:
  - name: ""
    function: ""
    holder: ""
    first_appearance: {chapter_num}
new_factions:
  - name: ""
    type: ""
    first_appearance: {chapter_num}
timeline_events:
  - story_time: ""
    event: ""
    chapter: {chapter_num}
new_abilities:
  - name: ""
    effect: ""
    user: ""
```
只输出 YAML，不要任何说明。
"""
    raw = agent.call_llm(prompt, temperature=0.2)
    yaml_content = raw.strip()
    for fence in ("```yaml", "```yml", "```"):
        if yaml_content.startswith(fence):
            yaml_content = yaml_content[len(fence):]
    if yaml_content.endswith("```"):
        yaml_content = yaml_content[:-3]

    try:
        return yaml.safe_load(yaml_content.strip()) or {}
    except yaml.YAMLError:
        return {}


def save_canon_update_request(project_root: Path, delta: dict, run_dir: Path) -> Path:
    """保存 Canon_Update_Request.yaml 到 run_dir。"""
    out = run_dir / f"Canon_Update_Request_Ch{delta.get('chapter', '?'):03d}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        yaml.dump(delta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return out


def append_new_characters_to_bible(project_root: Path, new_chars: list) -> str:
    """将新人物追加到 Character_Bible.md。"""
    if not new_chars:
        return ""
    path = project_root / "project_repo/canon/Character_Bible.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\n"]
    for c in new_chars:
        name = c.get("name", "未命名")
        lines.append(f"## {name}\n")
        lines.append(f"**基本信息**\n")
        lines.append(f"- 身份: {c.get('identity', '待补充')}\n")
        lines.append(f"- 首次出现: 第{c.get('first_appearance', '?')}章\n")
        lines.append(f"- 关键特征: {c.get('key_traits', '待补充')}\n")
        lines.append(f"\n**核心动机**: 待补充\n")
        lines.append(f"\n**变更日志**\n| 章节 | 变更内容 | 原因 |\n|-----|---------|------|\n\n---\n\n")
    with open(path, "a", encoding="utf-8") as f:
        f.writelines(lines)
    return f"已追加 {len(new_chars)} 个新人物到 Character_Bible"


def append_new_locations(project_root: Path, new_locs: list) -> str:
    if not new_locs:
        return ""
    path = project_root / "project_repo/canon/Location_Ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for loc in new_locs:
        name = loc.get("name", "未命名")
        row = f"| L{hash(name) % 1000:03d} | {name} | {loc.get('type', '?')} | — | {loc.get('description', '')} | {loc.get('first_appearance', '?')} | — |\n"
        lines.append(row)
    with open(path, "a", encoding="utf-8") as f:
        f.writelines(lines)
    return f"已追加 {len(new_locs)} 个新地点到 Location_Ledger"


def append_new_items(project_root: Path, new_items: list) -> str:
    if not new_items:
        return ""
    path = project_root / "project_repo/canon/Item_Ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for item in new_items:
        name = item.get("name", "未命名")
        row = f"| I{hash(name) % 1000:03d} | {name} | {item.get('function', '')} | {item.get('holder', '?')} | {item.get('first_appearance', '?')} | — | 持有中 |\n"
        lines.append(row)
    with open(path, "a", encoding="utf-8") as f:
        f.writelines(lines)
    return f"已追加 {len(new_items)} 个新道具到 Item_Ledger"


def append_timeline_events(project_root: Path, events: list) -> str:
    if not events:
        return ""
    path = project_root / "project_repo/canon/Timeline.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for ev in events:
        row = f"| 第{ev.get('chapter', '?')}章 | {ev.get('story_time', '?')} | {ev.get('event', '')} | — |\n"
        lines.append(row)
    with open(path, "a", encoding="utf-8") as f:
        f.writelines(lines)
    return f"已追加 {len(events)} 条时间线事件到 Timeline"


def run_extract_canon_delta(
    project_root: Path,
    chapter_num: int,
    chapter_content: str,
    run_dir: Path,
    auto_apply: bool = True,
) -> str:
    delta = extract_delta_with_llm(project_root, chapter_num, chapter_content)
    if not delta:
        return f"⚠️ 第{chapter_num}章 Canon Delta 提取失败或无新增设定"

    req_path = save_canon_update_request(project_root, delta, run_dir)
    messages = [f"✅ Canon Update Request 已保存: {req_path.name}"]

    if auto_apply:
        if delta.get("new_characters"):
            msg = append_new_characters_to_bible(project_root, delta["new_characters"])
            if msg:
                messages.append(f"  • {msg}")
        if delta.get("new_locations"):
            msg = append_new_locations(project_root, delta["new_locations"])
            if msg:
                messages.append(f"  • {msg}")
        if delta.get("new_items"):
            msg = append_new_items(project_root, delta["new_items"])
            if msg:
                messages.append(f"  • {msg}")
        if delta.get("timeline_events"):
            msg = append_timeline_events(project_root, delta["timeline_events"])
            if msg:
                messages.append(f"  • {msg}")

    return "\n".join(messages)


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    ch_num = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    manuscript = root / "project_repo/manuscript"
    content = ""
    if manuscript.exists():
        import re
        for vol_dir in sorted(manuscript.iterdir()):
            if vol_dir.is_dir():
                ch_file = vol_dir / f"ch{ch_num:03d}.md"
                if ch_file.exists():
                    content = ch_file.read_text(encoding="utf-8")
                    break
    if content:
        from pathlib import Path as _P
        run_d = root / "runs" / "CANON_DELTA"
        run_d.mkdir(parents=True, exist_ok=True)
        print(run_extract_canon_delta(root, ch_num, content, run_d))
    else:
        print(f"❌ 未找到第{ch_num}章内容")
