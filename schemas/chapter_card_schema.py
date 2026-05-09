"""
schemas/chapter_card_schema.py — ChapterCard 结构化数据模型

核心设计：
  - 每章写作必须有对应的结构化 ChapterCard
  - ChapterCard 单独解析，不能把整份章纲扔给 Writer
  - 支持从章纲 Markdown 解析，也支持 YAML 直接加载
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Scene:
    scene_id: str
    location: str = ""
    goal: str = ""
    conflict: str = ""
    turn: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Scene":
        return cls(
            scene_id=str(d.get("scene_id", "")),
            location=str(d.get("location", "")),
            goal=str(d.get("goal", "")),
            conflict=str(d.get("conflict", "")),
            turn=str(d.get("turn", "")),
            notes=str(d.get("notes", "")),
        )

    def to_dict(self) -> dict:
        return {k: v for k, v in {
            "scene_id": self.scene_id,
            "location": self.location,
            "goal": self.goal,
            "conflict": self.conflict,
            "turn": self.turn,
            "notes": self.notes,
        }.items() if v}


@dataclass
class ChapterCard:
    chapter: int
    title: str = ""
    word_target: int = 2000
    chapter_function: list[str] = field(default_factory=list)
    pov: str = ""
    scene_list: list[Scene] = field(default_factory=list)
    reader_payoff: list[str] = field(default_factory=list)
    foreshadowing: list[str] = field(default_factory=list)
    ending_hook: str = ""
    canon_updates: list[str] = field(default_factory=list)
    promise_opens: list[str] = field(default_factory=list)
    promise_closes: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "ChapterCard":
        scenes = [Scene.from_dict(s) if isinstance(s, dict) else Scene(scene_id=str(s)) for s in d.get("scene_list", [])]
        ending_hook = d.get("ending_hook", "")
        if isinstance(ending_hook, list):
            ending_hook = "\n".join(str(x) for x in ending_hook)
        return cls(
            chapter=int(d.get("chapter", 0)),
            title=str(d.get("title", "")),
            word_target=int(d.get("word_target", 2000)),
            chapter_function=list(d.get("chapter_function", [])),
            pov=str(d.get("pov", "")),
            scene_list=scenes,
            reader_payoff=list(d.get("reader_payoff", [])),
            foreshadowing=list(d.get("foreshadowing", [])),
            ending_hook=str(ending_hook),
            canon_updates=list(d.get("canon_updates", [])),
            promise_opens=list(d.get("promise_opens", [])),
            promise_closes=list(d.get("promise_closes", [])),
            notes=str(d.get("notes", "")),
        )

    def to_dict(self) -> dict:
        return {
            "chapter": self.chapter,
            "title": self.title,
            "word_target": self.word_target,
            "chapter_function": self.chapter_function,
            "pov": self.pov,
            "scene_list": [s.to_dict() for s in self.scene_list],
            "reader_payoff": self.reader_payoff,
            "foreshadowing": self.foreshadowing,
            "ending_hook": self.ending_hook,
            "canon_updates": self.canon_updates,
            "promise_opens": self.promise_opens,
            "promise_closes": self.promise_closes,
            "notes": self.notes,
        }

    def to_prompt_text(self) -> str:
        """生成用于 Chapter Writer 的章节卡片提示文本。"""
        lines = [
            f"## 第{self.chapter}章章节卡片",
            f"**标题**: {self.title or '（待定）'}",
            f"**目标字数**: {self.word_target}字",
            f"**视角**: {self.pov or '第三人称有限视角（主角）'}",
            "",
            "**章节功能**（此章必须完成的叙事任务）:",
        ]
        for fn in self.chapter_function:
            lines.append(f"  - {fn}")

        if self.scene_list:
            lines.append("\n**场景列表**:")
            for s in self.scene_list:
                lines.append(f"  - [{s.scene_id}] {s.location}")
                if s.goal:
                    lines.append(f"    目标: {s.goal}")
                if s.conflict:
                    lines.append(f"    冲突: {s.conflict}")
                if s.turn:
                    lines.append(f"    转折: {s.turn}")

        if self.reader_payoff:
            lines.append("\n**读者收益**（本章必须给读者的回报）:")
            for p in self.reader_payoff:
                lines.append(f"  - {p}")

        if self.foreshadowing:
            lines.append("\n**本章伏笔**:")
            for f_ in self.foreshadowing:
                lines.append(f"  - {f_}")

        lines.append(f"\n**结尾钩子**: {self.ending_hook or '（必须有明确钩子，不能平淡结尾）'}")

        if self.canon_updates:
            lines.append("\n**需要更新的 Canon**（写完正文后提取）:")
            for u in self.canon_updates:
                lines.append(f"  - {u}")

        return "\n".join(lines)


class ChapterCardIndex:
    """所有章节卡片的索引。支持 YAML 加载和持久化。"""

    def __init__(self, path: Optional[Path] = None):
        self.cards: dict[int, ChapterCard] = {}
        self.path = path
        if path and path.exists():
            self._load(path)

    def _load(self, path: Path) -> None:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        for c in raw.get("chapters", []):
            try:
                card = ChapterCard.from_dict(c)
                self.cards[card.chapter] = card
            except (ValueError, TypeError):
                pass

    def save(self, path: Optional[Path] = None) -> None:
        out = path or self.path
        if not out:
            raise ValueError("未指定保存路径")
        out.parent.mkdir(parents=True, exist_ok=True)
        data = {"chapters": [c.to_dict() for c in sorted(self.cards.values(), key=lambda x: x.chapter)]}
        with open(out, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def get(self, chapter_num: int) -> Optional[ChapterCard]:
        return self.cards.get(chapter_num)

    def has(self, chapter_num: int) -> bool:
        return chapter_num in self.cards

    def add(self, card: ChapterCard) -> None:
        self.cards[card.chapter] = card

    def missing_for_range(self, start: int, end: int) -> list[int]:
        return [i for i in range(start, end + 1) if i not in self.cards]

    def coverage_report(self) -> str:
        if not self.cards:
            return "ChapterCard 索引为空"
        nums = sorted(self.cards.keys())
        return f"已有章节卡片: 第{nums[0]}-{nums[-1]}章（共{len(nums)}张，缺失: {self.missing_for_range(nums[0], nums[-1])}）"
