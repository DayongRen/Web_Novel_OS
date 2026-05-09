"""
schemas/state_schema.py — 项目状态机数据模型

核心设计：
  - stages 从 list 改为 dict，记录每阶段详细状态
  - 记录依赖关系、失败原因、快照路径
  - 支持回滚查询
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


STAGE_DEPENDENCIES: dict[str, list[str]] = {
    "init":       [],
    "concept":    ["init"],
    "bible":      ["concept"],
    "outline":    ["bible"],
    "volume_001": ["outline"],
    "chapters":   ["volume_001"],
    "revision":   ["chapters"],
    "final":      ["revision"],
}

AGENT_TEMPERATURE: dict[str, float] = {
    "concept":    0.85,
    "bible":      0.45,
    "outline":    0.55,
    "volume_001": 0.75,
    "chapters":   0.75,
    "revision":   0.45,
    "validators": 0.20,
    "default":    0.70,
}


class StageStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    SKIPPED   = "skipped"


@dataclass
class StageRecord:
    status: StageStatus = StageStatus.PENDING
    run_id: str = ""
    snapshot_path: str = ""
    started_at: str = ""
    finished_at: str = ""
    error: str = ""
    run_count: int = 0

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "run_id": self.run_id,
            "snapshot_path": self.snapshot_path,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "run_count": self.run_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StageRecord":
        raw = d.get("status", "pending")
        try:
            status = StageStatus(raw)
        except ValueError:
            status = StageStatus.PENDING
        return cls(
            status=status,
            run_id=d.get("run_id", ""),
            snapshot_path=d.get("snapshot_path", ""),
            started_at=d.get("started_at", ""),
            finished_at=d.get("finished_at", ""),
            error=d.get("error", ""),
            run_count=int(d.get("run_count", 0)),
        )


@dataclass
class ProjectState:
    stages: dict[str, StageRecord] = field(default_factory=dict)
    current_chapter: int = 0
    total_words: int = 0
    last_good_snapshot: str = ""
    created_at: str = ""
    last_run: str = ""
    quality_gate_failures: list[str] = field(default_factory=list)

    ALL_STAGES = ["init", "concept", "bible", "outline", "volume_001", "chapters", "revision", "final"]

    def __post_init__(self):
        for s in self.ALL_STAGES:
            if s not in self.stages:
                self.stages[s] = StageRecord()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @classmethod
    def load(cls, path: Path) -> "ProjectState":
        if not path.exists():
            return cls()
        with open(path, encoding="utf-8") as f:
            d = json.load(f)

        obj = cls(
            current_chapter=d.get("current_chapter", 0),
            total_words=d.get("total_words", 0),
            last_good_snapshot=d.get("last_good_snapshot", ""),
            created_at=d.get("created_at", ""),
            last_run=d.get("last_run", ""),
            quality_gate_failures=d.get("quality_gate_failures", []),
        )
        for stage_name, stage_dict in d.get("stages", {}).items():
            obj.stages[stage_name] = StageRecord.from_dict(stage_dict)
        return obj

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        d = {
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "current_chapter": self.current_chapter,
            "total_words": self.total_words,
            "last_good_snapshot": self.last_good_snapshot,
            "created_at": self.created_at,
            "last_run": datetime.now().isoformat(),
            "quality_gate_failures": self.quality_gate_failures,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

    def is_done(self, stage: str) -> bool:
        return self.stages.get(stage, StageRecord()).status == StageStatus.DONE

    def is_failed(self, stage: str) -> bool:
        return self.stages.get(stage, StageRecord()).status == StageStatus.FAILED

    def can_run(self, stage: str) -> tuple[bool, str]:
        deps = STAGE_DEPENDENCIES.get(stage, [])
        for dep in deps:
            if not self.is_done(dep):
                dep_status = self.stages.get(dep, StageRecord()).status.value
                return False, f"依赖阶段 '{dep}' 未完成（当前状态: {dep_status}）"
        return True, ""

    def mark_started(self, stage: str, run_id: str) -> None:
        rec = self.stages.setdefault(stage, StageRecord())
        rec.status = StageStatus.RUNNING
        rec.run_id = run_id
        rec.started_at = datetime.now().isoformat()
        rec.run_count += 1
        rec.error = ""

    def mark_done(self, stage: str, snapshot_path: str = "") -> None:
        rec = self.stages.get(stage, StageRecord())
        rec.status = StageStatus.DONE
        rec.finished_at = datetime.now().isoformat()
        rec.snapshot_path = snapshot_path
        if snapshot_path:
            self.last_good_snapshot = snapshot_path

    def mark_failed(self, stage: str, error: str) -> None:
        rec = self.stages.get(stage, StageRecord())
        rec.status = StageStatus.FAILED
        rec.finished_at = datetime.now().isoformat()
        rec.error = error

    def current_stage(self) -> str:
        for s in self.ALL_STAGES:
            if not self.is_done(s):
                return s
        return "done"

    def get_temperature(self, stage: str) -> float:
        return AGENT_TEMPERATURE.get(stage, AGENT_TEMPERATURE["default"])
