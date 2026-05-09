"""
novel_studio/models.py — API 请求/响应 Pydantic 模型
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ── 请求模型 ──────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str
    idea: str
    genre: str = "urban_rebirth"
    target_words: int = 800000
    target_chapters: int = 400
    platform: str = "general_webnovel"


class CreateSessionRequest(BaseModel):
    project_id: Optional[str] = None
    initial_idea: str
    task_type: str = "full_flow"  # full_flow | bible_only | chapters | health_check


class DialogueResponseRequest(BaseModel):
    choice_id: Optional[str] = None    # A / B / C / D
    custom_text: Optional[str] = None  # 自定义输入


class GenerateRequest(BaseModel):
    task: str   # options | bible | chapter_cards | chapter | batch | health
    params: Dict[str, Any] = {}


class AcceptRequest(BaseModel):
    project_id: str
    files: List[str]               # 要采纳的文件相对路径列表
    accept_type: str = "official"  # official | draft | archive


class RewriteRequest(BaseModel):
    session_id: str
    file_path: str
    instruction: str
    intensity: str = "normal"      # light | normal | heavy


# ── 响应模型 ──────────────────────────────────────────────────────────────────

class OptionItem(BaseModel):
    id: str
    label: str
    description: str = ""
    pros: str = ""
    cons: str = ""


class DialogueTurn(BaseModel):
    role: str                       # "system" | "user"
    phase: str = ""
    question: str = ""
    context: str = ""
    options: List[OptionItem] = []
    allow_custom: bool = True
    user_choice: Optional[str] = None
    user_text: Optional[str] = None
    ready_to_generate: bool = False
    timestamp: str = ""


class ProjectInfo(BaseModel):
    project_id: str
    name: str
    genre: str
    target_words: int
    current_words: int = 0
    current_chapters: int = 0
    created_at: str
    last_active: str


class SessionInfo(BaseModel):
    session_id: str
    project_id: Optional[str]
    phase: str
    initial_idea: str
    turns_count: int
    generated_files: List[str]
    accepted_files: List[str]
    created_at: str
    updated_at: str


class TaskStatus(BaseModel):
    task_id: str
    status: str      # pending | running | done | failed
    progress: int = 0
    message: str = ""
    result_files: List[str] = []
    error: str = ""


class HealthReport(BaseModel):
    total_words: int
    total_chapters: int
    target_words: int
    completion_pct: float
    open_promises: int
    overdue_promises: int
    high_urgency_promises: int
    water_chapter_ratio: float
    hook_pass_rate: float
    status: str   # green | yellow | red
    issues: List[str]


class AcceptLog(BaseModel):
    session_id: str
    project_id: str
    accepted_files: List[str]
    accept_type: str
    timestamp: str
    diff_summary: str
