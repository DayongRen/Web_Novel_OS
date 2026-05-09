"""
schemas/project_profile.py — 项目画像数据模型

ProjectProfile 是 v2 系统的第一步产物，由 ProjectProfilerAgent 生成。
它决定后续所有策略的选择基础。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# ── 枚举 ──────────────────────────────────────────────────────────────────────

LENGTH_CLASSES = {
    "short_30k":    (0,       50_000),
    "novella_100k": (50_000,  150_000),
    "volume_200k":  (150_000, 300_000),
    "medium_500k":  (300_000, 800_000),
    "long_1m":      (800_000, 1_500_000),
    "epic_2m":      (1_500_000, 999_999_999),
}

CARD_POLICY_BY_LENGTH = {
    "short_30k":    "full_preplan",
    "novella_100k": "full_preplan",
    "volume_200k":  "full_preplan",
    "medium_500k":  "hybrid",
    "long_1m":      "rolling_window",
    "epic_2m":      "rolling_window",
}

AUTOMATION_LEVELS = ("full_auto", "guided", "human_in_loop")
HEAT_LEVELS = ("low", "medium", "high")
COMPLEXITY_LEVELS = ("simple", "medium", "complex", "epic")


def determine_length_class(word_count: int) -> str:
    for cls, (lo, hi) in LENGTH_CLASSES.items():
        if lo <= word_count < hi:
            return cls
    return "epic_2m"


def determine_card_policy(length_class: str) -> str:
    return CARD_POLICY_BY_LENGTH.get(length_class, "hybrid")


@dataclass
class ReaderContract:
    main_hook: str = ""
    core_expectation: str = ""
    emotional_payoff: str = ""
    plot_payoff: str = ""
    update_rhythm: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v}

    @classmethod
    def from_dict(cls, d: dict) -> "ReaderContract":
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})


@dataclass
class ProductionHints:
    automation_level: str = "guided"
    batch_size: int = 5
    review_interval_chapters: int = 20
    snapshot_interval_chapters: int = 5
    chapter_card_policy: str = "hybrid"

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> "ProductionHints":
        return cls(
            automation_level=d.get("automation_level", "guided"),
            batch_size=int(d.get("batch_size", 5)),
            review_interval_chapters=int(d.get("review_interval_chapters", 20)),
            snapshot_interval_chapters=int(d.get("snapshot_interval_chapters", 5)),
            chapter_card_policy=d.get("chapter_card_policy", "hybrid"),
        )


@dataclass
class RiskProfile:
    biggest_risks: list[str] = field(default_factory=list)
    required_ledgers: list[str] = field(default_factory=list)
    required_quality_gates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> "RiskProfile":
        return cls(
            biggest_risks=list(d.get("biggest_risks", [])),
            required_ledgers=list(d.get("required_ledgers", [])),
            required_quality_gates=list(d.get("required_quality_gates", [])),
        )


@dataclass
class ProjectProfile:
    title: str = ""
    original_idea: str = ""
    target_word_count: int = 200_000
    target_chapter_count: Optional[int] = None
    target_platform: str = ""
    audience: str = ""
    language: str = "zh"

    genre_primary: str = ""
    genre_secondary: list[str] = field(default_factory=list)
    tone: str = ""
    heat_level: str = "medium"
    complexity: str = "medium"

    length_class: str = "volume_200k"

    reader_contract: ReaderContract = field(default_factory=ReaderContract)
    production: ProductionHints = field(default_factory=ProductionHints)
    risk: RiskProfile = field(default_factory=RiskProfile)

    # 派生字段
    is_single_arc: bool = False
    needs_world_bible: bool = True
    needs_power_system: bool = False
    needs_faction_ledger: bool = False
    needs_case_ledger: bool = False
    needs_romance_arc: bool = False
    needs_resource_ledger: bool = False
    needs_instance_ledger: bool = False
    structure_model: str = "five_act"

    def __post_init__(self):
        if not self.length_class:
            self.length_class = determine_length_class(self.target_word_count)
        if not self.target_chapter_count:
            wpc = 2000 if self.target_word_count < 300_000 else 2200
            self.target_chapter_count = max(5, self.target_word_count // wpc)
        self.production.chapter_card_policy = determine_card_policy(self.length_class)
        self._infer_needs()

    def _infer_needs(self):
        g = self.genre_primary.lower()
        self.is_single_arc = self.length_class in ("short_30k", "novella_100k")
        self.needs_world_bible = self.complexity in ("complex", "epic") or g in (
            "xuanhuan", "xuanhuan_upgrade", "xianxia", "sci_fi", "sci_fi_mecha",
            "infinite_flow", "fantasy_xuanhuan"
        )
        self.needs_power_system = g in (
            "xuanhuan_upgrade", "xianxia", "xianxia_sect", "sci_fi_mecha",
            "infinite_flow", "fantasy_xuanhuan"
        )
        self.needs_faction_ledger = g in (
            "palace_intrigue", "fantasy_xuanhuan", "xuanhuan_upgrade",
            "xianxia", "xianxia_sect", "sci_fi"
        )
        self.needs_case_ledger = g in ("suspense", "suspense_crime")
        self.needs_romance_arc = g in ("romance_ceo", "romance", "jjwxc_female") or \
                                  "romance" in self.genre_secondary
        self.needs_resource_ledger = g in ("historical_farming", "survival", "farming")
        self.needs_instance_ledger = g in ("infinite_flow",)
        if self.length_class == "short_30k":
            self.structure_model = "single_arc"
        elif self.length_class == "novella_100k":
            self.structure_model = "three_act"
        elif self.length_class in ("volume_200k",):
            self.structure_model = "five_act_or_volume"
        elif self.length_class in ("medium_500k",):
            self.structure_model = "multi_volume"
        else:
            self.structure_model = "serial_longform"

    def to_dict(self) -> dict:
        return {
            "project": {
                "title": self.title,
                "original_idea": self.original_idea,
                "target_word_count": self.target_word_count,
                "target_chapter_count": self.target_chapter_count,
                "target_platform": self.target_platform,
                "audience": self.audience,
                "language": self.language,
            },
            "genre": {
                "primary": self.genre_primary,
                "secondary": self.genre_secondary,
                "tone": self.tone,
                "heat_level": self.heat_level,
                "complexity": self.complexity,
            },
            "length_class": {
                "name": self.length_class,
                "range": f"{LENGTH_CLASSES.get(self.length_class, (0,0))[0]:,} — {LENGTH_CLASSES.get(self.length_class, (0,0))[1]:,}",
                "recommended_stage_model": self.structure_model,
            },
            "reader_contract": self.reader_contract.to_dict(),
            "production": self.production.to_dict(),
            "risk_profile": self.risk.to_dict(),
            "inferred_needs": {
                "single_arc": self.is_single_arc,
                "world_bible": self.needs_world_bible,
                "power_system": self.needs_power_system,
                "faction_ledger": self.needs_faction_ledger,
                "case_ledger": self.needs_case_ledger,
                "romance_arc": self.needs_romance_arc,
                "resource_ledger": self.needs_resource_ledger,
                "instance_ledger": self.needs_instance_ledger,
            },
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    @classmethod
    def load(cls, path: Path) -> "ProjectProfile":
        if not path.exists():
            return cls()
        with open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        proj = d.get("project", {})
        genre = d.get("genre", {})
        prod = d.get("production", {})
        risk = d.get("risk_profile", {})
        contract = d.get("reader_contract", {})
        lc = d.get("length_class", {})

        obj = cls(
            title=proj.get("title", ""),
            original_idea=proj.get("original_idea", ""),
            target_word_count=int(proj.get("target_word_count", 200_000)),
            target_chapter_count=proj.get("target_chapter_count"),
            target_platform=proj.get("target_platform", ""),
            audience=proj.get("audience", ""),
            language=proj.get("language", "zh"),
            genre_primary=genre.get("primary", ""),
            genre_secondary=list(genre.get("secondary", [])),
            tone=genre.get("tone", ""),
            heat_level=genre.get("heat_level", "medium"),
            complexity=genre.get("complexity", "medium"),
            length_class=lc.get("name", ""),
            reader_contract=ReaderContract.from_dict(contract),
            production=ProductionHints.from_dict(prod),
            risk=RiskProfile.from_dict(risk),
        )
        return obj

    @property
    def words_per_chapter(self) -> int:
        if not self.target_chapter_count:
            return 2000
        return max(1000, self.target_word_count // self.target_chapter_count)
