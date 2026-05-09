"""
novel_studio/app.py — FastAPI 后端

运行方式：
  cd novel_studio
  uvicorn app:app --host 0.0.0.0 --port 8765 --reload
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import sandbox, generation
from .models import (
    AcceptRequest, CreateProjectRequest, CreateSessionRequest,
    DialogueResponseRequest, GenerateRequest, RewriteRequest,
)
from .sandbox import (
    accept_files, create_project, create_session, get_project,
    get_session, session_dir as get_session_dir, list_projects, list_sessions,
    project_word_count, save_generated_file, update_session,
    SESSIONS_DIR, PROJECTS_DIR,
)

STUDIO_DIR = Path(__file__).parent
app = FastAPI(title="Novel Studio API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = STUDIO_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    index = static_dir / "index.html"
    return HTMLResponse(index.read_text(encoding="utf-8"))


# ── 项目 API ──────────────────────────────────────────────────────────────────

@app.get("/api/projects")
async def api_list_projects():
    projects = list_projects()
    for p in projects:
        w, c = project_word_count(p["project_id"])
        p["current_words"] = w
        p["current_chapters"] = c
    return {"projects": projects}


@app.post("/api/projects/create")
async def api_create_project(req: CreateProjectRequest):
    meta = create_project(
        name=req.name, idea=req.idea, genre=req.genre,
        target_words=req.target_words, target_chapters=req.target_chapters,
        platform=req.platform,
    )
    return meta


@app.get("/api/projects/{project_id}")
async def api_get_project(project_id: str):
    meta = get_project(project_id)
    if not meta:
        raise HTTPException(404, f"项目 {project_id} 不存在")
    w, c = project_word_count(project_id)
    meta["current_words"] = w
    meta["current_chapters"] = c
    return meta


@app.get("/api/projects/{project_id}/files")
async def api_project_files(project_id: str):
    repo = sandbox.get_project_repo(project_id)
    if not repo.exists():
        return {"files": []}
    files = []
    for f in sorted(repo.rglob("*")):
        if f.is_file() and f.suffix in (".md", ".yaml", ".txt"):
            rel = str(f.relative_to(repo))
            size = f.stat().st_size
            files.append({"path": rel, "size": size, "type": _file_type(rel)})
    return {"files": files}


@app.get("/api/projects/{project_id}/file")
async def api_read_project_file(project_id: str, path: str):
    repo = sandbox.get_project_repo(project_id)
    full = (repo / path).resolve()
    if not str(full).startswith(str(repo)):
        raise HTTPException(403, "路径越界")
    if not full.exists():
        raise HTTPException(404, f"文件不存在: {path}")
    return {"path": path, "content": full.read_text(encoding="utf-8")}


@app.get("/api/projects/{project_id}/health")
async def api_project_health(project_id: str, chapter: int = 0):
    from tools import (run_word_budget_check, run_pacing_check, run_hook_check,
                       run_promise_check, run_continuity_check)
    from schemas.promise_schema import PromisePayoffMap

    repo_root = sandbox.get_project_repo(project_id).parent
    config = sandbox.get_project_config(project_id)
    pm_path = repo_root / "project_repo/continuity/Promise_Payoff_Map.yaml"
    pm = PromisePayoffMap.load(pm_path)
    h = pm.health_check(chapter)

    pacing = run_pacing_check(repo_root, config)
    water = pacing.count("💧水")
    total_ch = max(pacing.count("| 第"), 1)

    hook = run_hook_check(repo_root)
    hook_pass = hook.count("✅") + hook.count("🔥")
    hook_total = max(hook.count("| 第"), 1)

    w, c = project_word_count(project_id)
    target = config.get("project", {}).get("target_word_count", 1)

    issues = []
    if h["overdue"] > 0:
        issues.append(f"逾期承诺 {h['overdue']} 条：{', '.join(h['overdue_ids'])}")
    if h["open"] > 12:
        issues.append(f"开放承诺过多：{h['open']} 条（上限12）")
    water_ratio = water / total_ch
    if water_ratio > 0.25:
        issues.append(f"水章比例偏高：{water_ratio:.0%}")

    status = "green"
    if issues:
        status = "red" if h["overdue"] > 0 else "yellow"

    return {
        "total_words": w, "total_chapters": c,
        "target_words": target, "completion_pct": round(w / max(target, 1) * 100, 1),
        "open_promises": h["open"], "overdue_promises": h["overdue"],
        "high_urgency_promises": h["high_urgency"],
        "water_chapter_ratio": round(water_ratio, 2),
        "hook_pass_rate": round(hook_pass / hook_total, 2),
        "status": status, "issues": issues,
    }


# ── Session API ───────────────────────────────────────────────────────────────

@app.get("/api/sessions")
async def api_list_sessions(project_id: str = None):
    return {"sessions": list_sessions(project_id)}


@app.post("/api/sessions/create")
async def api_create_session(req: CreateSessionRequest):
    state = create_session(req.project_id, req.initial_idea, req.task_type)
    return state


@app.get("/api/sessions/{session_id}")
async def api_get_session(session_id: str):
    state = get_session(session_id)
    if not state:
        raise HTTPException(404, f"Session {session_id} 不存在")
    return state


@app.get("/api/sessions/{session_id}/files")
async def api_session_files(session_id: str):
    sess_d = get_session_dir(session_id)
    if not sess_d.exists():
        return {"files": []}
    files = []
    for f in sorted(sess_d.rglob("*")):
        if f.is_file() and f.suffix in (".md", ".yaml", ".txt", ".json"):
            rel = str(f.relative_to(sess_d))
            files.append({"path": rel, "size": f.stat().st_size, "type": _file_type(rel)})
    return {"files": files}


@app.get("/api/sessions/{session_id}/file")
async def api_read_session_file(session_id: str, path: str):
    sess_d = get_session_dir(session_id)
    full = (sess_d / path).resolve()
    if not str(full).startswith(str(sess_d)):
        raise HTTPException(403, "路径越界")
    if not full.exists():
        raise HTTPException(404, f"文件不存在: {path}")
    return {"path": path, "content": full.read_text(encoding="utf-8")}


# ── 对话 API ──────────────────────────────────────────────────────────────────

@app.post("/api/sessions/{session_id}/dialogue/start")
async def api_dialogue_start(session_id: str):
    """生成第一个引导问题。"""
    state = get_session(session_id)
    if not state:
        raise HTTPException(404)

    project_id = state.get("project_id")
    config = sandbox.get_project_config(project_id) if project_id else _base_config()
    if project_id:
        project_root = sandbox.get_project_repo(project_id).parent
    else:
        project_root = Path(__file__).parent.parent

    from llm import make_client
    from agents.interactive_director import InteractiveDirectorAgent
    client = make_client(config)
    agent = InteractiveDirectorAgent(config, project_root, client)

    sess_dir = get_session_dir(session_id)
    turn = agent.generate_first_question(state["initial_idea"], sess_dir)
    turn["timestamp"] = _now()

    turns = state.get("dialogue_turns", [])
    turns.append({"role": "system", **turn})
    update_session(session_id, {"dialogue_turns": turns, "phase": turn.get("phase", "story_focus")})
    return turn


@app.post("/api/sessions/{session_id}/dialogue/respond")
async def api_dialogue_respond(session_id: str, req: DialogueResponseRequest):
    """用户回答引导问题，系统给出下一个问题或判定就绪。"""
    state = get_session(session_id)
    if not state:
        raise HTTPException(404)

    turns = state.get("dialogue_turns", [])
    last_system_turn = next((t for t in reversed(turns) if t.get("role") == "system"), {})
    options = last_system_turn.get("options", [])
    current_phase = last_system_turn.get("phase", "story_focus")

    collected = state.get("collected", {})
    project_id = state.get("project_id")
    config = sandbox.get_project_config(project_id) if project_id else _base_config()
    project_root = sandbox.get_project_repo(project_id).parent if project_id else Path(__file__).parent.parent

    from llm import make_client
    from agents.interactive_director import InteractiveDirectorAgent
    client = make_client(config)
    agent = InteractiveDirectorAgent(config, project_root, client)

    collected = agent.integrate_user_choice(
        collected, current_phase, req.choice_id, req.custom_text, options
    )

    user_turn = {
        "role": "user", "phase": current_phase,
        "choice_id": req.choice_id, "custom_text": req.custom_text,
        "timestamp": _now(),
    }
    turns.append(user_turn)

    next_turn = agent.generate_next_question(
        state["initial_idea"], collected, current_phase, get_session_dir(session_id)
    )
    next_turn["timestamp"] = _now()
    turns.append({"role": "system", **next_turn})

    update_session(session_id, {
        "dialogue_turns": turns,
        "collected": collected,
        "phase": next_turn.get("phase", "ready"),
    })
    return next_turn


# ── 生成 API ──────────────────────────────────────────────────────────────────

@app.post("/api/sessions/{session_id}/generate")
async def api_generate(session_id: str, req: GenerateRequest):
    state = get_session(session_id)
    if not state:
        raise HTTPException(404)
    task_id = generation.start_task(session_id, req.task, req.params)
    return {"task_id": task_id, "status": "pending"}


@app.get("/api/tasks/{task_id}")
async def api_task_status(task_id: str):
    t = generation.get_task(task_id)
    if not t:
        raise HTTPException(404, f"任务 {task_id} 不存在")
    return t


@app.post("/api/sessions/{session_id}/rewrite")
async def api_rewrite(session_id: str, req: RewriteRequest):
    state = get_session(session_id)
    if not state:
        raise HTTPException(404)
    task_id = generation.start_task(session_id, "rewrite", {
        "file_path": req.file_path,
        "instruction": req.instruction,
        "intensity": req.intensity,
    })
    return {"task_id": task_id}


# ── 采纳 API ──────────────────────────────────────────────────────────────────

@app.post("/api/accept")
async def api_accept(req: AcceptRequest):
    log = accept_files(
        session_id=req.session_id,  # 从 session 的 session_id 取，但 req 里也有
        project_id=req.project_id,
        files=req.files,
        accept_type=req.accept_type,
    )

    # accept_files 需要 session_id，从 session 数据里找
    # 补丁：重新绑定
    return log


@app.post("/api/sessions/{session_id}/accept")
async def api_session_accept(session_id: str, req: AcceptRequest):
    log = accept_files(
        session_id=session_id,
        project_id=req.project_id,
        files=req.files,
        accept_type=req.accept_type,
    )
    return log


# ── 类型/模板 API ─────────────────────────────────────────────────────────────

@app.get("/api/genres")
async def api_genres():
    genre_dir = Path(__file__).parent.parent / "templates/genre_profiles"
    genres = []
    if genre_dir.exists():
        import yaml
        for f in sorted(genre_dir.glob("*.yaml")):
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            genres.append({
                "id": f.stem,
                "display_name": data.get("display_name", f.stem),
                "typical_length": data.get("typical_length", ""),
                "target_gender": data.get("target_gender", "neutral"),
            })
    return {"genres": genres}


@app.get("/api/tasks")
async def api_task_list():
    return [
        {"id": "options", "label": "生成候选方案", "icon": "🎯"},
        {"id": "bible", "label": "生成故事圣经", "icon": "📚"},
        {"id": "chapter_cards", "label": "生成章节卡片", "icon": "🃏"},
        {"id": "chapter", "label": "写一章正文", "icon": "✍️"},
        {"id": "batch", "label": "批量写章节", "icon": "📖"},
        {"id": "health", "label": "健康度检查", "icon": "🏥"},
    ]


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


def _base_config() -> dict:
    import yaml
    cfg = Path(__file__).parent.parent / "novel_config.yaml"
    if cfg.exists():
        with open(cfg, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _file_type(rel: str) -> str:
    name = rel.lower()
    if "chapter" in name or name.startswith("ch"):
        return "chapter"
    if "bible" in name or "canon" in name:
        return "canon"
    if "promise" in name or "continuity" in name or "thread" in name:
        return "continuity"
    if "outline" in name or "card" in name:
        return "outline"
    if "report" in name or "pacing" in name or "health" in name:
        return "report"
    return "other"
