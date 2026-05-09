"""
schemas/promise_schema.py — Promise-Payoff Map 的数据模型与合并逻辑

核心设计：
  - LLM 只能输出 patch（add / update / close），不能整表覆盖
  - 每次写入前 schema 校验
  - 合并时保护已有记录，防止 ID 丢失
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml


class PromiseType(str, Enum):
    REVENGE = "revenge"
    ROMANCE = "romance"
    UPGRADE = "upgrade"
    MYSTERY = "mystery"
    IDENTITY = "identity"
    TREASURE = "treasure"
    PUNISHMENT = "punishment"
    RELATIONSHIP_REPAIR = "relationship_repair"
    POWER = "power"
    TRUTH = "truth"
    BUSINESS = "business"
    OTHER = "other"


class PromiseStatus(str, Enum):
    OPEN = "open"
    PLANNED = "planned"
    PARTIAL = "partial"
    CLOSED = "closed"
    ABANDONED = "abandoned"


class Urgency(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PayoffWindow:
    start: int
    end: int

    @classmethod
    def parse(cls, raw) -> "PayoffWindow":
        if isinstance(raw, dict):
            return cls(start=int(raw.get("start", 0)), end=int(raw.get("end", 999)))
        s = str(raw)
        nums = re.findall(r"\d+", s)
        if len(nums) >= 2:
            return cls(start=int(nums[0]), end=int(nums[1]))
        if len(nums) == 1:
            v = int(nums[0])
            return cls(start=v, end=v + 20)
        return cls(start=0, end=999)

    def is_overdue(self, current_chapter: int) -> bool:
        return current_chapter > self.end

    def is_urgent(self, current_chapter: int) -> bool:
        return current_chapter > self.start + (self.end - self.start) * 0.5

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end}


@dataclass
class Promise:
    id: str
    chapter_opened: int
    type: PromiseType
    promise: str
    expected_payoff_window: PayoffWindow
    status: PromiseStatus = PromiseStatus.OPEN
    payoff_plan: str = ""
    urgency: Urgency = Urgency.MEDIUM
    last_updated_chapter: int = 0
    notes: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Promise":
        pid = str(d.get("id", ""))
        if not pid:
            raise ValueError("Promise 缺少 id 字段")

        raw_type = d.get("type", "other")
        try:
            ptype = PromiseType(raw_type)
        except ValueError:
            ptype = PromiseType.OTHER

        raw_status = d.get("status", "open")
        try:
            status = PromiseStatus(raw_status)
        except ValueError:
            status = PromiseStatus.OPEN

        raw_urgency = d.get("urgency", "medium")
        try:
            urgency = Urgency(raw_urgency)
        except ValueError:
            urgency = Urgency.MEDIUM

        return cls(
            id=pid,
            chapter_opened=int(d.get("chapter_opened", 0)),
            type=ptype,
            promise=str(d.get("promise", "")),
            expected_payoff_window=PayoffWindow.parse(d.get("expected_payoff_window", "0-999")),
            status=status,
            payoff_plan=str(d.get("payoff_plan", "")),
            urgency=urgency,
            last_updated_chapter=int(d.get("last_updated_chapter", 0)),
            notes=str(d.get("notes", "")),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "chapter_opened": self.chapter_opened,
            "type": self.type.value,
            "promise": self.promise,
            "expected_payoff_window": self.expected_payoff_window.to_dict(),
            "status": self.status.value,
            "payoff_plan": self.payoff_plan,
            "urgency": self.urgency.value,
            "last_updated_chapter": self.last_updated_chapter,
            "notes": self.notes,
        }


@dataclass
class PromisePatch:
    """LLM 输出的变更 patch，不允许整表替换。"""
    add_promises: list[dict] = field(default_factory=list)
    update_promises: list[dict] = field(default_factory=list)
    close_promises: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "PromisePatch":
        return cls(
            add_promises=d.get("add_promises", []),
            update_promises=d.get("update_promises", []),
            close_promises=d.get("close_promises", []),
        )


@dataclass
class PromisePayoffMap:
    promises: dict[str, Promise] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "PromisePayoffMap":
        if not path.exists():
            return cls()
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        obj = cls()
        for p_dict in raw.get("promises", []):
            try:
                p = Promise.from_dict(p_dict)
                obj.promises[p.id] = p
            except (ValueError, KeyError):
                pass
        return obj

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"promises": [p.to_dict() for p in sorted(self.promises.values(), key=lambda x: x.id)]}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def apply_patch(self, patch: PromisePatch, current_chapter: int) -> list[str]:
        """应用 patch，返回变更日志列表。"""
        log: list[str] = []

        for p_dict in patch.add_promises:
            try:
                p = Promise.from_dict(p_dict)
                if p.id in self.promises:
                    log.append(f"⚠️  SKIP ADD {p.id}：ID 已存在（用 update 修改）")
                else:
                    p.last_updated_chapter = current_chapter
                    self.promises[p.id] = p
                    log.append(f"✅ ADD {p.id}：{p.promise[:60]}")
            except (ValueError, KeyError) as e:
                log.append(f"❌ ADD 失败（schema 错误）: {e} | raw: {p_dict}")

        for p_dict in patch.update_promises:
            pid = str(p_dict.get("id", ""))
            if pid not in self.promises:
                log.append(f"⚠️  SKIP UPDATE {pid}：ID 不存在")
                continue
            existing = self.promises[pid]
            for key, val in p_dict.items():
                if key == "id":
                    continue
                if key == "status":
                    try:
                        existing.status = PromiseStatus(val)
                    except ValueError:
                        log.append(f"⚠️  {pid} status 值无效: {val}")
                elif key == "urgency":
                    try:
                        existing.urgency = Urgency(val)
                    except ValueError:
                        pass
                elif key == "payoff_plan":
                    existing.payoff_plan = str(val)
                elif key == "notes":
                    existing.notes = str(val)
                elif key == "expected_payoff_window":
                    existing.expected_payoff_window = PayoffWindow.parse(val)
            existing.last_updated_chapter = current_chapter
            log.append(f"✅ UPDATE {pid}")

        for p_dict in patch.close_promises:
            pid = str(p_dict.get("id", ""))
            if pid not in self.promises:
                log.append(f"⚠️  SKIP CLOSE {pid}：ID 不存在")
                continue
            self.promises[pid].status = PromiseStatus.CLOSED
            self.promises[pid].last_updated_chapter = current_chapter
            note = p_dict.get("payoff_note", "")
            if note:
                self.promises[pid].notes = note
            log.append(f"✅ CLOSE {pid}")

        return log

    def health_check(self, current_chapter: int) -> dict:
        open_ps = [p for p in self.promises.values() if p.status in (PromiseStatus.OPEN, PromiseStatus.PLANNED)]
        overdue = [p for p in open_ps if p.expected_payoff_window.is_overdue(current_chapter)]
        high_urgency = [p for p in open_ps if p.urgency == Urgency.HIGH]
        return {
            "total": len(self.promises),
            "open": len(open_ps),
            "overdue": len(overdue),
            "overdue_ids": [p.id for p in overdue],
            "high_urgency": len(high_urgency),
            "high_urgency_ids": [p.id for p in high_urgency],
            "closed": sum(1 for p in self.promises.values() if p.status == PromiseStatus.CLOSED),
        }

    def next_id(self) -> str:
        if not self.promises:
            return "P001"
        nums = []
        for pid in self.promises:
            m = re.search(r"\d+", pid)
            if m:
                nums.append(int(m.group()))
        return f"P{(max(nums) + 1):03d}" if nums else "P001"
