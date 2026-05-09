"""
novel_studio/generation.py — 后台生成任务执行器

把 Studio 请求转换为对 agents 的实际调用，结果写入 session sandbox。
所有生成都先进 session，不直接写 project_repo。
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from . import sandbox
from .sandbox import SESSIONS_DIR, session_dir as get_session_dir, save_generated_file

TASKS: dict[str, dict] = {}
_lock = threading.Lock()


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _task_id() -> str:
    return f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:20]}"


def start_task(session_id: str, task_type: str, params: dict) -> str:
    tid = _task_id()
    with _lock:
        TASKS[tid] = {"task_id": tid, "status": "pending", "progress": 0,
                      "message": "排队中...", "result_files": [], "error": ""}
    t = threading.Thread(target=_run_task, args=(tid, session_id, task_type, params), daemon=True)
    t.start()
    return tid


def get_task(task_id: str) -> Optional[dict]:
    return TASKS.get(task_id)


def _update(tid: str, **kw) -> None:
    with _lock:
        if tid in TASKS:
            TASKS[tid].update(kw)


def _run_task(tid: str, session_id: str, task_type: str, params: dict) -> None:
    _update(tid, status="running", message="运行中...")
    try:
        state = sandbox.get_session(session_id) or {}
        project_id = state.get("project_id")

        if project_id:
            config = sandbox.get_project_config(project_id)
            project_root = sandbox.get_project_repo(project_id).parent
        else:
            config = _load_base_config()
            project_root = Path(__file__).parent.parent

        # 把 session 收集的信息注入 config
        collected = state.get("collected", {})
        if "genre" in collected:
            config.setdefault("genre", {})["primary"] = collected["genre"]

        from llm import make_client
        client = make_client(config)

        sess_dir = get_session_dir(session_id)
        result_files = []

        if task_type == "options":
            result_files = _gen_options(client, config, project_root, sess_dir, session_id, state, params)
        elif task_type == "bible":
            result_files = _gen_bible(client, config, project_root, sess_dir, session_id, state, params)
        elif task_type == "chapter_cards":
            result_files = _gen_chapter_cards(client, config, project_root, sess_dir, session_id, state, params)
        elif task_type == "chapter":
            result_files = _gen_chapter(client, config, project_root, sess_dir, session_id, state, params)
        elif task_type == "batch":
            result_files = _gen_batch(client, config, project_root, sess_dir, session_id, state, params)
        elif task_type == "health":
            result_files = _gen_health(config, project_root, sess_dir, session_id)
        elif task_type == "rewrite":
            result_files = _rewrite(client, config, project_root, sess_dir, session_id, state, params)
        else:
            raise ValueError(f"未知任务类型: {task_type}")

        _update(tid, status="done", progress=100, message="完成", result_files=result_files)

    except Exception as e:
        import traceback
        _update(tid, status="failed", message=str(e), error=traceback.format_exc())


# ── 各任务实现 ────────────────────────────────────────────────────────────────

def _gen_options(client, config, project_root, sess_dir, session_id, state, params) -> list[str]:
    from agents.interactive_director import InteractiveDirectorAgent
    agent = InteractiveDirectorAgent(config, project_root, client)
    idea = state.get("initial_idea", "")
    collected = state.get("collected", {})
    task_label = params.get("task", "故事框架方案")
    n = params.get("n", 3)

    options = agent.generate_options(idea, collected, task_label, n, sess_dir)

    content = f"# {task_label} — {n}个候选方案\n\n"
    for opt in options:
        content += f"## {opt.get('option_id', '?')}: {opt.get('title', '')}\n\n"
        content += f"**摘要**: {opt.get('summary', '')}\n\n"
        if opt.get("key_features"):
            content += "**特点**:\n"
            for feat in opt["key_features"]:
                content += f"- {feat}\n"
            content += "\n"
        content += f"**优点**: {opt.get('pros', '')}\n"
        content += f"**风险**: {opt.get('cons', '')}\n"
        content += f"**适合**: {opt.get('best_for', '')}\n\n"
        content += "---\n\n"
        content += opt.get("content", "") + "\n\n---\n\n"

    rel = save_generated_file(session_id, "concept_options.md", content)

    raw_json = json.dumps(options, ensure_ascii=False, indent=2)
    rel2 = save_generated_file(session_id, "concept_options_raw.json", raw_json)
    return [rel, rel2]


def _gen_bible(client, config, project_root, sess_dir, session_id, state, params) -> list[str]:
    from agents import CharacterKeeperAgent, WorldbuildingKeeperAgent, StyleKeeperAgent
    collected = state.get("collected", {})
    _inject_collected_to_repo(collected, project_root)

    files = []
    run_dir = sess_dir / "generated"

    wb = WorldbuildingKeeperAgent(config, project_root, client)
    wb.build_world_bible(run_dir)
    rel = save_generated_file(session_id, "World_Bible.md",
                              (run_dir / "World_Bible.md").read_text(encoding="utf-8"))
    files.append(rel)

    ck = CharacterKeeperAgent(config, project_root, client)
    ck.build_character_bible(run_dir)
    rel2 = save_generated_file(session_id, "Character_Bible.md",
                               (run_dir / "Character_Bible.md").read_text(encoding="utf-8"))
    files.append(rel2)

    sk = StyleKeeperAgent(config, project_root, client)
    sk.build_voice_guide(run_dir)
    rel3 = save_generated_file(session_id, "Voice_Guide.md",
                               (run_dir / "Voice_Guide.md").read_text(encoding="utf-8"))
    files.append(rel3)

    from agents import PlotArchitectAgent
    pa = PlotArchitectAgent(config, project_root, client)
    pa.generate_full_outline(run_dir)
    rel4 = save_generated_file(session_id, "Full_Outline.md",
                               (run_dir / "Full_Outline.md").read_text(encoding="utf-8"))
    files.append(rel4)

    return files


def _gen_chapter_cards(client, config, project_root, sess_dir, session_id, state, params) -> list[str]:
    from agents import PlotArchitectAgent
    from tools import parse_cards_with_llm
    run_dir = sess_dir / "generated"
    start = params.get("start", 1)
    end = params.get("end", 30)

    pa = PlotArchitectAgent(config, project_root, client)
    pa.generate_chapter_outlines(start, end, run_dir)

    outline_text = (run_dir / f"Chapter_Outlines_{start:03d}_{end:03d}.md").read_text(encoding="utf-8")
    rel = save_generated_file(session_id, f"Chapter_Outlines_{start:03d}_{end:03d}.md", outline_text)

    msg = parse_cards_with_llm(project_root, force=True)
    cards_path = project_root / "project_repo/outlines/chapter_cards.yaml"
    if cards_path.exists():
        cards_content = cards_path.read_text(encoding="utf-8")
        rel2 = save_generated_file(session_id, "chapter_cards.yaml", cards_content)
        return [rel, rel2]

    return [rel]


def _gen_chapter(client, config, project_root, sess_dir, session_id, state, params) -> list[str]:
    from agents import ChapterWriterAgent
    from schemas.chapter_card_schema import ChapterCard, ChapterCardIndex

    ch_num = params.get("chapter", 1)
    card_path = project_root / "project_repo/outlines/chapter_cards.yaml"
    idx = ChapterCardIndex(card_path if card_path.exists() else None)
    card = idx.get(ch_num) or ChapterCard(
        chapter=ch_num, title=f"第{ch_num}章",
        word_target=config.get("project", {}).get("words_per_chapter", 2000)
    )

    writer = ChapterWriterAgent(config, project_root, client)
    vol_dir = sess_dir / "generated" / "manuscript"
    vol_dir.mkdir(parents=True, exist_ok=True)
    content = writer.write_chapter(ch_num, card, sess_dir / "generated", vol_dir)

    rel = save_generated_file(session_id, f"ch{ch_num:03d}.md", content)
    return [rel]


def _gen_batch(client, config, project_root, sess_dir, session_id, state, params) -> list[str]:
    start = params.get("start", 1)
    batch = params.get("batch", 5)
    files = []
    for i in range(start, start + batch):
        result = _gen_chapter(client, config, project_root, sess_dir, session_id, state, {"chapter": i})
        files.extend(result)
    return files


def _gen_health(config, project_root, sess_dir, session_id) -> list[str]:
    from tools import (run_word_budget_check, run_pacing_check, run_hook_check,
                       run_promise_check, run_continuity_check)
    state = sandbox.get_session(session_id) or {}
    project_id = state.get("project_id")
    if project_id:
        repo_root = sandbox.get_project_repo(project_id).parent
    else:
        repo_root = project_root

    ch = state.get("collected", {}).get("current_chapter", 0)
    reports = {
        "字数预算": run_word_budget_check(repo_root),
        "节奏检查": run_pacing_check(repo_root, config),
        "钩子质量": run_hook_check(repo_root),
        "承诺-回报": run_promise_check(repo_root, ch),
        "连续性": run_continuity_check(repo_root),
    }
    combined = "# 项目健康度报告\n\n"
    for name, rpt in reports.items():
        combined += f"## {name}\n\n{rpt}\n\n---\n\n"

    rel = save_generated_file(session_id, "health_report.md", combined)
    return [rel]


def _rewrite(client, config, project_root, sess_dir, session_id, state, params) -> list[str]:
    from agents import ChapterWriterAgent
    from schemas.chapter_card_schema import ChapterCard, ChapterCardIndex

    file_path = params.get("file_path", "")
    instruction = params.get("instruction", "")

    src = get_session_dir(session_id) / file_path
    if not src.exists():
        if project_id := state.get("project_id"):
            repo_path = sandbox.get_project_repo(project_id)
            src = repo_path / file_path

    if not src.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    original = src.read_text(encoding="utf-8")

    from agents.base_agent import BaseAgent
    agent = BaseAgent(config, project_root, client)
    prompt = f"""
原文：
{original}

重写指令：{instruction}

请根据指令重写以上内容。保留原文的基本情节骨架，只按指令方向调整。
直接输出重写后的内容，不要解释。
"""
    result = agent.call_llm(prompt, temperature=0.8)
    filename = f"rewrite_{src.name}"
    rel = save_generated_file(session_id, filename, result)
    return [rel]


def _inject_collected_to_repo(collected: dict, project_root: Path) -> None:
    """把已收集的设定信息注入到 project_repo 的核心创意文件。"""
    idea_path = project_root / "project_repo/outlines/00_core_idea.md"
    if not idea_path.exists() or not collected:
        return
    existing = idea_path.read_text(encoding="utf-8")
    additions = "\n\n## 创作方向选择（用户确认）\n\n"
    for phase, value in collected.items():
        if isinstance(value, dict):
            additions += f"- **{phase}**: {value.get('label', '')} — {value.get('description', '')}\n"
        else:
            additions += f"- **{phase}**: {value}\n"
    idea_path.write_text(existing + additions, encoding="utf-8")


def _load_base_config() -> dict:
    cfg_path = Path(__file__).parent.parent / "novel_config.yaml"
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}
