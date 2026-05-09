"""
schemas/production_strategy.py — 生产策略数据模型

ProductionStrategy 是系统真正的执行蓝图，
由 ProductionStrategyAgent 根据 ProjectProfile + 三组模板生成。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ChapterCardPolicy:
    mode: str = "hybrid"             # full_preplan | hybrid | rolling_window
    rolling_window_size: int = 30    # rolling 模式下提前规划多少章
    hybrid_current_vol_detail: int = 50  # hybrid 模式下当前卷详细规划章数

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> "ChapterCardPolicy":
        return cls(
            mode=d.get("mode", "hybrid"),
            rolling_window_size=int(d.get("rolling_window_size", 30)),
            hybrid_current_vol_detail=int(d.get("hybrid_current_vol_detail", 50)),
        )


@dataclass
class BatchPolicy:
    write_batch_size: int = 5
    quality_check_every: int = 5
    structural_review_every: int = 20
    major_reoutline_every: int = 50
    snapshot_every: int = 10
    export_every: int = 0  # 0 = 只在结束时导出

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> "BatchPolicy":
        return cls(**{k: int(d.get(k, v)) for k, v in cls.__dataclass_fields__.items()})


@dataclass
class QualityPolicy:
    hard_fail: list[str] = field(default_factory=lambda: [
        "missing_chapter_card", "empty_chapter", "canon_contradiction"
    ])
    warn_only: list[str] = field(default_factory=lambda: [
        "weak_hook", "pacing_slow", "side_character_flat"
    ])
    active_gates: list[str] = field(default_factory=lambda: [
        "universal", "length_specific"
    ])

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> "QualityPolicy":
        return cls(
            hard_fail=list(d.get("hard_fail", [])),
            warn_only=list(d.get("warn_only", [])),
            active_gates=list(d.get("active_gates", [])),
        )


@dataclass
class FailurePolicy:
    missing_chapter_card: str = "stop_and_repair_outline"
    generation_exception: str = "retry_same_chapter"
    max_retries: int = 3
    weak_hook: str = "warn_and_continue"
    canon_contradiction: str = "stop_and_generate_repair_plan"
    major_arc_drift: str = "structural_review_then_reoutline"
    cost_limit_reached: str = "pause_and_request_user_decision"
    pacing_slow: str = "warn_and_continue"

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> "FailurePolicy":
        obj = cls()
        for k in obj.__dataclass_fields__:
            if k in d:
                if k == "max_retries":
                    setattr(obj, k, int(d[k]))
                else:
                    setattr(obj, k, d[k])
        return obj


@dataclass
class StageDefinition:
    id: str
    required: bool = True
    conditional_on: str = ""   # ledger or agent that must exist
    skip_if: str = ""          # condition to skip

    def to_dict(self) -> dict:
        d = {"id": self.id, "required": self.required}
        if self.conditional_on:
            d["conditional_on"] = self.conditional_on
        if self.skip_if:
            d["skip_if"] = self.skip_if
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "StageDefinition":
        return cls(
            id=d.get("id", ""),
            required=d.get("required", True),
            conditional_on=d.get("conditional_on", ""),
            skip_if=d.get("skip_if", ""),
        )


@dataclass
class ExportConfig:
    artifacts: list[str] = field(default_factory=list)
    format: list[str] = field(default_factory=lambda: ["md", "txt"])
    include_docx: bool = True

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> "ExportConfig":
        return cls(
            artifacts=list(d.get("artifacts", [])),
            format=list(d.get("format", ["md", "txt"])),
            include_docx=bool(d.get("include_docx", True)),
        )


@dataclass
class ProductionStrategy:
    length_profile: str = "volume_200k"
    genre_profile: str = "urban_rebirth"
    platform_profile: str = "web_serial_general"
    structure_model: str = "five_act_or_volume"
    target_chapters: int = 100
    words_per_chapter: int = 2000
    total_word_budget: int = 200_000

    stages: list[StageDefinition] = field(default_factory=list)
    chapter_card_policy: ChapterCardPolicy = field(default_factory=ChapterCardPolicy)
    batch_policy: BatchPolicy = field(default_factory=BatchPolicy)
    quality_policy: QualityPolicy = field(default_factory=QualityPolicy)
    failure_policy: FailurePolicy = field(default_factory=FailurePolicy)
    export_config: ExportConfig = field(default_factory=ExportConfig)

    required_ledgers: list[str] = field(default_factory=list)
    active_agents: list[str] = field(default_factory=list)

    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "strategy": {
                "length_profile": self.length_profile,
                "genre_profile": self.genre_profile,
                "platform_profile": self.platform_profile,
                "structure_model": self.structure_model,
                "target_chapters": self.target_chapters,
                "words_per_chapter": self.words_per_chapter,
                "total_word_budget": self.total_word_budget,
            },
            "stages": [s.to_dict() for s in self.stages],
            "chapter_card_policy": self.chapter_card_policy.to_dict(),
            "batch_policy": self.batch_policy.to_dict(),
            "quality_policy": self.quality_policy.to_dict(),
            "failure_policy": self.failure_policy.to_dict(),
            "export_config": self.export_config.to_dict(),
            "required_ledgers": self.required_ledgers,
            "active_agents": self.active_agents,
            "notes": self.notes,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    @classmethod
    def load(cls, path: Path) -> Optional["ProductionStrategy"]:
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}

        s = d.get("strategy", {})
        obj = cls(
            length_profile=s.get("length_profile", "volume_200k"),
            genre_profile=s.get("genre_profile", "urban_rebirth"),
            platform_profile=s.get("platform_profile", "web_serial_general"),
            structure_model=s.get("structure_model", "five_act"),
            target_chapters=int(s.get("target_chapters", 100)),
            words_per_chapter=int(s.get("words_per_chapter", 2000)),
            total_word_budget=int(s.get("total_word_budget", 200_000)),
            stages=[StageDefinition.from_dict(x) for x in d.get("stages", [])],
            chapter_card_policy=ChapterCardPolicy.from_dict(d.get("chapter_card_policy", {})),
            batch_policy=BatchPolicy.from_dict(d.get("batch_policy", {})),
            quality_policy=QualityPolicy.from_dict(d.get("quality_policy", {})),
            failure_policy=FailurePolicy.from_dict(d.get("failure_policy", {})),
            export_config=ExportConfig.from_dict(d.get("export_config", {})),
            required_ledgers=list(d.get("required_ledgers", [])),
            active_agents=list(d.get("active_agents", [])),
            notes=d.get("notes", ""),
        )
        return obj

    @classmethod
    def default_for_profile(cls, profile: "ProjectProfile") -> "ProductionStrategy":
        """从 ProjectProfile 创建默认策略（无需 LLM）。"""
        from schemas.project_profile import LENGTH_CLASSES

        bp = BatchPolicy(
            write_batch_size=3 if profile.length_class == "short_30k" else 5,
            quality_check_every=3 if profile.length_class == "short_30k" else 5,
            structural_review_every=10 if profile.length_class in ("short_30k", "novella_100k") else 20,
            major_reoutline_every=999 if profile.is_single_arc else 50,
        )

        ledgers = ["Character_Bible", "Promise_Ledger"]
        if profile.needs_world_bible:
            ledgers.append("World_Bible")
        if profile.needs_power_system:
            ledgers.append("Power_System_Ledger")
        if profile.needs_faction_ledger:
            ledgers.append("Faction_Ledger")
        if profile.needs_case_ledger:
            ledgers.append("Case_Ledger")
        if profile.needs_romance_arc:
            ledgers.append("Relationship_Arc_Ledger")
        if profile.needs_resource_ledger:
            ledgers.append("Resource_Ledger")
        if profile.needs_instance_ledger:
            ledgers.append("Instance_Ledger")
        if profile.length_class not in ("short_30k",):
            ledgers.append("Arc_Tracker")
        if profile.length_class in ("long_1m", "epic_2m"):
            ledgers.extend(["Timeline", "Faction_Ledger"])

        stages = [
            StageDefinition("init"), StageDefinition("profile"),
            StageDefinition("strategy"), StageDefinition("bible"),
            StageDefinition("outline"), StageDefinition("produce"),
            StageDefinition("revision"), StageDefinition("export"),
        ]

        exports = ["final.md", "final.txt"]
        if profile.length_class in ("long_1m", "epic_2m"):
            exports += ["chapter_index.md", "global_timeline.md", "unresolved_threads.md"]
        elif profile.length_class not in ("short_30k",):
            exports += ["chapter_index.md", "continuity_report.md"]

        return cls(
            length_profile=profile.length_class,
            genre_profile=profile.genre_primary,
            platform_profile=profile.target_platform or "web_serial_general",
            structure_model=profile.structure_model,
            target_chapters=profile.target_chapter_count or 100,
            words_per_chapter=profile.words_per_chapter,
            total_word_budget=profile.target_word_count,
            stages=stages,
            chapter_card_policy=ChapterCardPolicy(
                mode=profile.production.chapter_card_policy
            ),
            batch_policy=bp,
            quality_policy=QualityPolicy(
                active_gates=["universal", "length_specific", "genre_specific"]
            ),
            required_ledgers=list(dict.fromkeys(ledgers)),
            export_config=ExportConfig(artifacts=exports),
        )
