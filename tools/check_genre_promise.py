"""
tools/check_genre_promise.py — 类型承诺硬校验器

检查当前已写章节是否满足类型范本规定的核心承诺和开篇要求。
在 init/前10章/前30章节点强制执行。

使用：
  python -m tools.check_genre_promise [project_root] [current_chapter]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).parent.parent


def load_config(project_root: Path) -> dict:
    p = project_root / "novel_config.yaml"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_genre_profile(project_root: Path, genre: str) -> dict:
    p = project_root / f"templates/genre_profiles/{genre}.yaml"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_chapters(project_root: Path, up_to: int) -> list[dict]:
    manuscript = project_root / "project_repo/manuscript"
    chapters = []
    if not manuscript.exists():
        return chapters
    for vol_dir in sorted(manuscript.iterdir()):
        if vol_dir.is_dir():
            for ch_file in sorted(vol_dir.glob("ch*.md")):
                m = re.search(r"ch(\d+)", ch_file.stem)
                if m:
                    num = int(m.group(1))
                    if num <= up_to:
                        chapters.append({"num": num, "content": ch_file.read_text(encoding="utf-8")})
    return sorted(chapters, key=lambda x: x["num"])


def _text_contains_any(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def check_opening_requirements(genre_profile: dict, chapters: list[dict]) -> list[dict]:
    """检查开篇要求（前1/3/10章）"""
    issues = []
    opening = genre_profile.get("opening_requirements", {})

    ch_texts = {ch["num"]: ch["content"] for ch in chapters}
    all_text_upto = {
        n: "\n".join(ch_texts[i] for i in range(1, n + 1) if i in ch_texts)
        for n in [1, 3, 10, 30]
    }

    first_1000 = list(ch_texts.values())[0][:1000] if ch_texts else ""
    for req in opening.get("first_1000_words", []):
        issues.append({
            "checkpoint": "前1000字",
            "requirement": req,
            "status": "MANUAL_CHECK",
            "note": "需要人工确认"
        })

    if len(chapters) >= 3:
        text_3 = all_text_upto.get(3, "")
        for req in opening.get("first_3_chapters", []):
            issues.append({
                "checkpoint": "前3章",
                "requirement": req,
                "status": "MANUAL_CHECK",
                "note": "需要人工确认"
            })

    if len(chapters) >= 10:
        text_10 = all_text_upto.get(10, "")
        for req in opening.get("first_10_chapters", []):
            issues.append({
                "checkpoint": "前10章",
                "requirement": req,
                "status": "MANUAL_CHECK",
                "note": "需要人工确认"
            })

    return issues


def check_core_promises_against_payoff_map(
    genre_profile: dict, project_root: Path, current_chapter: int
) -> list[dict]:
    """检查类型核心承诺是否在 Promise_Payoff_Map 中有对应条目"""
    issues = []
    pm_path = project_root / "project_repo/continuity/Promise_Payoff_Map.yaml"
    if not pm_path.exists():
        issues.append({
            "checkpoint": "Promise_Payoff_Map",
            "requirement": "承诺追踪表必须存在",
            "status": "FAIL",
            "note": "Promise_Payoff_Map.yaml 不存在"
        })
        return issues

    with open(pm_path, encoding="utf-8") as f:
        pm = yaml.safe_load(f) or {}

    promise_texts = " ".join(
        str(p.get("promise", "")) + " " + str(p.get("type", ""))
        for p in pm.get("promises", [])
    ).lower()

    type_keywords = {
        "revenge": ["复仇", "仇", "报仇"],
        "romance": ["爱情", "感情", "喜欢", "爱上"],
        "upgrade": ["升级", "突破", "变强", "成长"],
        "mystery": ["谜团", "秘密", "真相", "隐藏"],
        "identity": ["身份", "身世", "来历"],
        "face_slapping": ["打脸", "逆袭"],
        "weak_to_strong": ["弱", "强", "崛起"],
        "survival_pressure": ["生死", "死亡", "危险", "生存"],
    }

    for promise in genre_profile.get("core_promises", []):
        pid = promise.get("id", "")
        keywords = type_keywords.get(pid, [pid.replace("_", "")])
        found = _text_contains_any(promise_texts, keywords)
        issues.append({
            "checkpoint": f"核心承诺[{pid}]",
            "requirement": promise.get("description", pid),
            "status": "FOUND" if found else "MISSING",
            "note": "" if found else f"承诺追踪表中未找到此类型承诺，可能尚未登记"
        })

    return issues


def run_genre_promise_check(project_root: Path, current_chapter: int = 0) -> str:
    config = load_config(project_root)
    genre = config.get("genre", {}).get("primary", "")

    if not genre:
        return "# 类型承诺检查\n\n⚠️ novel_config.yaml 未设置 genre.primary"

    genre_profile = load_genre_profile(project_root, genre)
    if not genre_profile:
        return f"# 类型承诺检查\n\n⚠️ 未找到类型范本: templates/genre_profiles/{genre}.yaml"

    chapters = load_chapters(project_root, current_chapter or 9999)

    lines = [
        f"# 类型承诺检查报告\n",
        f"**类型**: {genre} ({genre_profile.get('display_name', genre)})\n",
        f"**当前章节**: 第{current_chapter}章\n",
        f"**已写章节**: {len(chapters)}章\n",
    ]

    if not chapters:
        lines.append("ℹ️  暂无已写章节，请在写完前10章后重新检查。\n")
    else:
        opening_issues = check_opening_requirements(genre_profile, chapters)
        lines.append("## 开篇要求检查\n")
        for issue in opening_issues:
            icon = {"PASS": "✅", "FAIL": "❌", "MANUAL_CHECK": "🔍", "WARN": "⚠️"}.get(issue["status"], "?")
            lines.append(f"- {icon} [{issue['checkpoint']}] {issue['requirement']}")
            if issue.get("note"):
                lines.append(f"  _{issue['note']}_")

    pm_issues = check_core_promises_against_payoff_map(genre_profile, project_root, current_chapter)
    lines.append("\n## 核心承诺登记状态\n")
    missing = [i for i in pm_issues if i["status"] == "MISSING"]
    found = [i for i in pm_issues if i["status"] == "FOUND"]
    lines.append(f"已登记: {len(found)} | 未登记: {len(missing)}\n")
    for issue in pm_issues:
        icon = "✅" if issue["status"] == "FOUND" else "❌"
        lines.append(f"- {icon} {issue['requirement']}")
        if issue.get("note"):
            lines.append(f"  _{issue['note']}_")

    avoid = genre_profile.get("avoid", [])
    if avoid:
        lines.append("\n## 类型禁区提醒（需人工确认）\n")
        for item in avoid:
            lines.append(f"- ⚠️ 禁止: {item}")

    fail_count = len(missing)
    lines.append(f"\n## 总结\n")
    if fail_count == 0:
        lines.append("✅ 所有核心承诺已登记，开篇要求需人工确认。")
    else:
        lines.append(f"❌ {fail_count} 条核心承诺尚未在 Promise_Payoff_Map 中登记，建议补充。")

    return "\n".join(lines)


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    ch = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(run_genre_promise_check(root, ch))
