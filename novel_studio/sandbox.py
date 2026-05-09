"""
novel_studio/sandbox.py — Session Sandbox + Project Sandbox 管理
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

STUDIO_ROOT = Path(__file__).parent
WORKSPACE_ROOT = STUDIO_ROOT.parent
PROJECTS_DIR = STUDIO_ROOT / "sandbox" / "projects"
SESSIONS_DIR = STUDIO_ROOT / "sandbox" / "sessions"


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(name: str) -> str:
    import re
    s = re.sub(r"[^\w一-鿿]", "_", name.lower())
    return re.sub(r"_+", "_", s).strip("_")[:40]


# ── Project Sandbox ───────────────────────────────────────────────────────────

def create_project(name: str, idea: str, genre: str, target_words: int,
                   target_chapters: int, platform: str) -> dict:
    ts_short = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_id = f"{_slug(name)}_{ts_short}"
    project_dir = PROJECTS_DIR / project_id

    template_repo = WORKSPACE_ROOT / "project_repo"
    if template_repo.exists():
        shutil.copytree(template_repo, project_dir / "project_repo",
                        ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
    else:
        (project_dir / "project_repo" / "outlines").mkdir(parents=True)
        (project_dir / "project_repo" / "canon").mkdir(parents=True)
        (project_dir / "project_repo" / "continuity").mkdir(parents=True)
        (project_dir / "project_repo" / "manuscript").mkdir(parents=True)

    (project_dir / "project_repo" / "outlines" / "00_core_idea.md").write_text(
        idea, encoding="utf-8"
    )

    template_cfg = WORKSPACE_ROOT / "novel_config.yaml"
    cfg: dict = {}
    if template_cfg.exists():
        with open(template_cfg, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    cfg.setdefault("project", {}).update({
        "title": name,
        "target_word_count": target_words,
        "target_chapter_count": target_chapters,
        "target_platform": platform,
    })
    cfg.setdefault("genre", {})["primary"] = genre

    with open(project_dir / "project_config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

    meta = {
        "project_id": project_id,
        "name": name,
        "genre": genre,
        "target_words": target_words,
        "target_chapters": target_chapters,
        "platform": platform,
        "created_at": _ts(),
        "last_active": _ts(),
    }
    with open(project_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    (project_dir / "runs").mkdir(parents=True, exist_ok=True)
    (project_dir / "snapshots").mkdir(parents=True, exist_ok=True)
    return meta


def list_projects() -> list[dict]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for p in sorted(PROJECTS_DIR.iterdir()):
        meta_f = p / "meta.json"
        if meta_f.exists():
            with open(meta_f, encoding="utf-8") as f:
                result.append(json.load(f))
    return result


def get_project(project_id: str) -> Optional[dict]:
    meta_f = PROJECTS_DIR / project_id / "meta.json"
    if meta_f.exists():
        with open(meta_f, encoding="utf-8") as f:
            return json.load(f)
    return None


def get_project_config(project_id: str) -> dict:
    cfg_f = PROJECTS_DIR / project_id / "project_config.yaml"
    if cfg_f.exists():
        with open(cfg_f, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    template = WORKSPACE_ROOT / "novel_config.yaml"
    if template.exists():
        with open(template, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_project_repo(project_id: str) -> Path:
    return PROJECTS_DIR / project_id / "project_repo"


def project_word_count(project_id: str) -> tuple[int, int]:
    """返回 (total_words, total_chapters)。"""
    manuscript = get_project_repo(project_id) / "manuscript"
    words, chapters = 0, 0
    if manuscript.exists():
        for f in manuscript.rglob("ch*.md"):
            words += len(f.read_text(encoding="utf-8"))
            chapters += 1
    return words, chapters


# ── Session Sandbox ───────────────────────────────────────────────────────────

def create_session(project_id: Optional[str], initial_idea: str, task_type: str) -> dict:
    ts_short = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
    session_id = f"session_{ts_short}"
    session_dir = SESSIONS_DIR / session_id

    for sub in ("input", "generated", "reports", "logs"):
        (session_dir / sub).mkdir(parents=True)

    (session_dir / "input" / "user_brief.md").write_text(initial_idea, encoding="utf-8")

    state = {
        "session_id": session_id,
        "project_id": project_id,
        "task_type": task_type,
        "phase": "gathering",
        "initial_idea": initial_idea,
        "dialogue_turns": [],
        "collected": {},
        "generated_files": [],
        "accepted_files": [],
        "created_at": _ts(),
        "updated_at": _ts(),
    }
    _save_session_state(session_id, state)
    return state


def get_session(session_id: str) -> Optional[dict]:
    return _load_session_state(session_id)


def list_sessions(project_id: Optional[str] = None) -> list[dict]:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for s in sorted(SESSIONS_DIR.iterdir(), reverse=True):
        state = _load_session_state(s.name)
        if state:
            if project_id is None or state.get("project_id") == project_id:
                result.append({
                    "session_id": state["session_id"],
                    "project_id": state.get("project_id"),
                    "phase": state.get("phase"),
                    "initial_idea": state["initial_idea"][:80],
                    "turns_count": len(state.get("dialogue_turns", [])),
                    "generated_files": state.get("generated_files", []),
                    "accepted_files": state.get("accepted_files", []),
                    "created_at": state.get("created_at"),
                    "updated_at": state.get("updated_at"),
                })
    return result


def update_session(session_id: str, updates: dict) -> dict:
    state = _load_session_state(session_id) or {}
    state.update(updates)
    state["updated_at"] = _ts()
    _save_session_state(session_id, state)
    return state


def session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / session_id


def save_generated_file(session_id: str, filename: str, content: str) -> str:
    """保存生成文件到 session/generated/，返回相对路径。"""
    p = SESSIONS_DIR / session_id / "generated" / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    state = _load_session_state(session_id) or {}
    files = state.get("generated_files", [])
    rel = f"generated/{filename}"
    if rel not in files:
        files.append(rel)
    state["generated_files"] = files
    state["updated_at"] = _ts()
    _save_session_state(session_id, state)
    return rel


def accept_files(session_id: str, project_id: str, files: list[str], accept_type: str) -> dict:
    """把 session 生成文件采纳到 project_repo，返回 Accept Log。"""
    import difflib

    session_d = SESSIONS_DIR / session_id
    project_repo = get_project_repo(project_id)
    accepted = []
    diff_lines = []

    for rel in files:
        src = session_d / rel
        if not src.exists():
            continue
        filename = src.name
        ext = src.suffix

        if ext in (".md", ".yaml", ".yml"):
            dest_dir = _infer_dest_dir(filename, project_repo)
        else:
            dest_dir = project_repo / "manuscript"

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename

        old_text = dest.read_text(encoding="utf-8") if dest.exists() else ""
        new_text = src.read_text(encoding="utf-8")
        diff = list(difflib.unified_diff(
            old_text.splitlines(), new_text.splitlines(),
            fromfile=f"before/{filename}", tofile=f"after/{filename}", lineterm=""
        ))
        diff_lines.extend(diff[:50])

        shutil.copy2(src, dest)
        accepted.append(str(dest.relative_to(project_repo)))

    log = {
        "session_id": session_id,
        "project_id": project_id,
        "accepted_files": accepted,
        "accept_type": accept_type,
        "timestamp": _ts(),
        "diff_summary": "\n".join(diff_lines[:100]),
    }

    log_path = session_d / "logs" / f"accept_{datetime.now().strftime('%H%M%S')}.json"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    state = _load_session_state(session_id) or {}
    acc = state.get("accepted_files", [])
    acc.extend(accepted)
    state["accepted_files"] = acc
    state["updated_at"] = _ts()
    _save_session_state(session_id, state)

    meta_f = PROJECTS_DIR / project_id / "meta.json"
    if meta_f.exists():
        with open(meta_f, encoding="utf-8") as f:
            meta = json.load(f)
        meta["last_active"] = _ts()
        with open(meta_f, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    return log


def _infer_dest_dir(filename: str, project_repo: Path) -> Path:
    name = filename.lower()
    if "bible" in name or "world" in name or "character" in name or \
       "power" in name or "faction" in name or "timeline" in name or \
       "relationship" in name or "item" in name or "location" in name:
        return project_repo / "canon"
    if "outline" in name or "logline" in name or "core_idea" in name:
        return project_repo / "outlines"
    if "promise" in name or "foreshadow" in name or "mystery" in name or \
       "arc_tracker" in name or "open_thread" in name or "backlog" in name:
        return project_repo / "continuity"
    if "voice" in name or "dialogue_guide" in name or "pov" in name or \
       "forbidden" in name or "tone" in name:
        return project_repo / "style"
    if "synopsis" in name or "selling" in name or "title" in name or \
       "hook" in name or "tag" in name or "target" in name:
        return project_repo / "market"
    if "chapter_card" in name:
        return project_repo / "outlines"
    if name.startswith("ch") and name[2:5].isdigit():
        return project_repo / "manuscript" / "volume_001"
    return project_repo / "outlines"


def _load_session_state(session_id: str) -> Optional[dict]:
    p = SESSIONS_DIR / session_id / "session_state.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_session_state(session_id: str, state: dict) -> None:
    p = SESSIONS_DIR / session_id / "session_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
