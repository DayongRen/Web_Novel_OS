"""
tools/ledger_registry.py — 账本注册表管理

根据 Production_Strategy 和 Project_Profile 中的 required_ledgers，
初始化对应的账本模板文件。不存在则创建，已存在不覆盖。
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent

LEDGER_TEMPLATES: dict[str, dict] = {
    "Character_Bible": {
        "path": "project_repo/canon/Character_Bible.md",
        "type": "md",
    },
    "World_Bible": {
        "path": "project_repo/canon/World_Bible.md",
        "type": "md",
    },
    "Power_System_Ledger": {
        "path": "project_repo/canon/Power_System_Ledger.yaml",
        "type": "yaml",
        "template": {"levels": [], "resources": [], "rules": [], "protagonist_special": {}},
    },
    "Promise_Ledger": {
        "path": "project_repo/continuity/Promise_Payoff_Map.yaml",
        "type": "yaml",
        "template": {"promises": []},
    },
    "Arc_Tracker": {
        "path": "project_repo/continuity/Character_Arc_Tracker.yaml",
        "type": "yaml",
        "template": {"characters": []},
    },
    "Faction_Ledger": {
        "path": "project_repo/canon/Faction_Ledger.yaml",
        "type": "yaml",
        "template": {"factions": []},
    },
    "Case_Ledger": {
        "path": "project_repo/canon/Case_Ledger.yaml",
        "type": "yaml",
        "template": {"cases": [], "clues": [], "suspects": [], "reveals": []},
    },
    "Relationship_Arc_Ledger": {
        "path": "project_repo/canon/Relationship_Arc_Ledger.yaml",
        "type": "yaml",
        "template": {"pairs": [], "emotional_beats": [], "milestones": []},
    },
    "Resource_Ledger": {
        "path": "project_repo/canon/Resource_Ledger.yaml",
        "type": "yaml",
        "template": {"resources": [], "transactions": [], "current_holdings": {}},
    },
    "Instance_Ledger": {
        "path": "project_repo/canon/Instance_Ledger.yaml",
        "type": "yaml",
        "template": {"instances": [], "global_rules": [], "items": []},
    },
    "Timeline": {
        "path": "project_repo/canon/Timeline.md",
        "type": "md",
    },
    "Item_Ledger": {
        "path": "project_repo/canon/Item_Ledger.md",
        "type": "md",
    },
    "Location_Ledger": {
        "path": "project_repo/canon/Location_Ledger.md",
        "type": "md",
    },
    "Upgrade_Ledger": {
        "path": "project_repo/continuity/Upgrade_Ledger.yaml",
        "type": "yaml",
        "template": {"protagonist_upgrades": [], "bottlenecks": [], "current_level": ""},
    },
    "Clue_Ledger": {
        "path": "project_repo/canon/Clue_Ledger.yaml",
        "type": "yaml",
        "template": {"clues": []},
    },
    "Suspect_Ledger": {
        "path": "project_repo/canon/Suspect_Ledger.yaml",
        "type": "yaml",
        "template": {"suspects": []},
    },
    "Reveal_Map": {
        "path": "project_repo/canon/Reveal_Map.yaml",
        "type": "yaml",
        "template": {"reveals": []},
    },
    "Alliance_Map": {
        "path": "project_repo/canon/Alliance_Map.yaml",
        "type": "yaml",
        "template": {"alliances": [], "betrayals": []},
    },
    "Survival_Risk_Ledger": {
        "path": "project_repo/continuity/Survival_Risk_Ledger.yaml",
        "type": "yaml",
        "template": {"current_risks": [], "team_status": [], "resources_remaining": []},
    },
    "Team_Ledger": {
        "path": "project_repo/canon/Team_Ledger.yaml",
        "type": "yaml",
        "template": {"members": []},
    },
    "Rule_Ledger": {
        "path": "project_repo/canon/Rule_Ledger.yaml",
        "type": "yaml",
        "template": {"instances": []},
    },
    "Emotional_Beat_Map": {
        "path": "project_repo/continuity/Emotional_Beat_Map.yaml",
        "type": "yaml",
        "template": {"beats": []},
    },
}

_MD_TEMPLATES: dict[str, str] = {
    "Character_Bible": "# 人物圣经\n\n> 所有主要人物档案（由系统自动更新）\n\n",
    "World_Bible": "# 世界观圣经\n\n> 由 Worldbuilding Keeper 生成\n\n",
    "Timeline": "# 时间线\n\n| 章节 | 故事时间 | 事件 |\n|-----|---------|------|\n",
    "Item_Ledger": "# 道具账本\n\n| ID | 名称 | 功能 | 持有者 | 首次出现 | 状态 |\n|----|------|------|--------|---------|------|\n",
    "Location_Ledger": "# 地点账本\n\n| ID | 名称 | 类型 | 区域 | 描述 | 首次出现 |\n|----|------|------|------|------|----------|\n",
}


def init_ledgers(project_root: Path, required_ledgers: list[str]) -> dict[str, str]:
    """
    初始化账本。已存在的不覆盖，不在 required 中的不创建。
    返回 {ledger_name: status} 字典，status 为 'created' | 'exists' | 'unknown'。
    """
    result: dict[str, str] = {}

    registry_path = project_root / "project_repo/canon/Ledger_Registry.yaml"
    registry: dict = {"ledgers": {}}

    for name in required_ledgers:
        tpl = LEDGER_TEMPLATES.get(name)
        if not tpl:
            result[name] = "unknown"
            continue

        full_path = project_root / tpl["path"]
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if full_path.exists():
            result[name] = "exists"
        else:
            if tpl["type"] == "yaml":
                data = tpl.get("template", {})
                with open(full_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            else:
                content = _MD_TEMPLATES.get(name, f"# {name}\n\n")
                full_path.write_text(content, encoding="utf-8")
            result[name] = "created"

        registry["ledgers"][name] = {
            "required": True,
            "path": tpl["path"],
            "type": tpl["type"],
            "status": result[name],
        }

    with open(registry_path, "w", encoding="utf-8") as f:
        yaml.dump(registry, f, allow_unicode=True, default_flow_style=False)

    return result


def get_active_ledgers(project_root: Path) -> dict[str, str]:
    """返回已存在的账本 {name: path}。"""
    registry_path = project_root / "project_repo/canon/Ledger_Registry.yaml"
    if not registry_path.exists():
        return {}
    with open(registry_path, encoding="utf-8") as f:
        reg = yaml.safe_load(f) or {}
    result = {}
    for name, info in reg.get("ledgers", {}).items():
        full = project_root / info.get("path", "")
        if full.exists():
            result[name] = info["path"]
    return result


def report_ledger_status(project_root: Path) -> str:
    active = get_active_ledgers(project_root)
    lines = ["# 账本状态\n"]
    for name, path in sorted(active.items()):
        full = project_root / path
        size = full.stat().st_size if full.exists() else 0
        lines.append(f"- ✅ **{name}**: `{path}` ({size:,}B)")
    return "\n".join(lines)


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    print(report_ledger_status(root))
