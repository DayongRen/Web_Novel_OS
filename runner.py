#!/usr/bin/env python3
"""
Web Novel OS v2 — 自适应长篇小说生产系统 主运行器

v2 新增命令：
  profile   — 生成项目画像（Project_Profile.yaml）
  strategy  — 生成生产策略（Production_Strategy.yaml）
  produce   — 通用自适应生产阶段（替代固定的 volume_001 + chapters）
  cards     — 生成/补充章节卡片（支持三种 policy）
  export    — 自适应导出（根据 length_profile 决定产物）

兼容 v1 命令：
  init / run / status / check / snapshot / rollback / cost

用法示例：
  python runner.py init          # 初始化
  python runner.py profile       # 生成项目画像
  python runner.py strategy      # 生成生产策略
  python runner.py run --stage bible
  python runner.py cards         # 根据 strategy 生成章卡
  python runner.py produce       # 通用生产循环
  python runner.py produce --batch 3 --until 50
  python runner.py export
  python runner.py status
  python runner.py check
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

PROJECT_ROOT = Path(__file__).parent
console = Console()

STATE_PATH = PROJECT_ROOT / "runs" / ".state.json"
COST_LOG_PATH = PROJECT_ROOT / "runs" / "_cost_report.json"

V2_STAGES = ["init", "profile", "strategy", "bible", "outline", "produce", "revision", "export"]
V1_STAGES = ["init", "concept", "bible", "outline", "volume_001", "chapters", "revision", "final"]

STAGE_LABELS = {
    "init":       "000_Init — 项目初始化",
    "profile":    "001_Profile — 项目画像生成",
    "strategy":   "002_Strategy — 生产策略生成",
    "concept":    "001_Concept — 概念包生成",
    "bible":      "003_Bible — 故事圣经",
    "outline":    "004_Outline — 总纲大纲",
    "volume_001": "005_Volume_001 — 第一卷",
    "chapters":   "006_Chapters — 批量写章节",
    "produce":    "005_Produce — 通用生产",
    "revision":   "007_Revision — 修订",
    "final":      "008_Final — 最终导出",
    "export":     "008_Export — 自适应导出",
}


# ── 配置与状态 ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    p = PROJECT_ROOT / "novel_config.yaml"
    if not p.exists():
        console.print("[red]❌ novel_config.yaml 不存在[/red]")
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_state():
    from schemas.state_schema import ProjectState
    return ProjectState.load(STATE_PATH)


def save_state(state) -> None:
    state.save(STATE_PATH)


def load_profile():
    from schemas.project_profile import ProjectProfile
    p = PROJECT_ROOT / "project_repo/manifests/Project_Profile.yaml"
    if p.exists():
        return ProjectProfile.load(p)
    return None


def load_strategy():
    from schemas.production_strategy import ProductionStrategy
    p = PROJECT_ROOT / "project_repo/manifests/Production_Strategy.yaml"
    return ProductionStrategy.load(p)


def make_run_dir(stage_name: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "runs" / f"{stage_name.upper()}" / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def freeze_snapshot(stage_name: str, label: str = "") -> Path:
    folder = stage_name.upper()
    if label:
        folder += f"_{label}"
    snap_dir = PROJECT_ROOT / "snapshots" / folder
    if snap_dir.exists():
        shutil.rmtree(snap_dir)
    shutil.copytree(
        PROJECT_ROOT / "project_repo",
        snap_dir,
        ignore=shutil.ignore_patterns("*.pyc", "__pycache__"),
    )
    console.print(f"  📸 快照: [dim]{snap_dir.name}[/dim]")
    return snap_dir


def count_words() -> tuple[int, int]:
    manuscript = PROJECT_ROOT / "project_repo/manuscript"
    words, chapters = 0, 0
    if manuscript.exists():
        for f in manuscript.rglob("ch*.md"):
            words += len(f.read_text(encoding="utf-8"))
            chapters += 1
    return words, chapters


def _make_client(config: dict):
    from llm import make_client
    return make_client(config)


def _make_router(config: dict, client=None):
    from agents.agent_router import AgentRouter
    return AgentRouter(config, PROJECT_ROOT, client)


def _save_cost(stage: str, client) -> None:
    if not hasattr(client, "cost_summary"):
        return
    summary = client.cost_summary()
    summary["stage"] = stage
    summary["timestamp"] = datetime.now().isoformat()
    existing = []
    if COST_LOG_PATH.exists():
        with open(COST_LOG_PATH, encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except Exception:
                existing = []
    existing.append(summary)
    COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(COST_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


# ── v2 阶段实现 ───────────────────────────────────────────────────────────────

def run_stage_profile(config: dict, state, run_dir: Path) -> None:
    """生成 Project_Profile.yaml。"""
    from agents.project_profiler import ProjectProfilerAgent

    core_idea_path = PROJECT_ROOT / "project_repo/outlines/00_core_idea.md"
    idea = core_idea_path.read_text(encoding="utf-8") if core_idea_path.exists() else ""
    if not idea.strip():
        console.print("[red]❌ 00_core_idea.md 为空，请先填写创意[/red]")
        sys.exit(1)

    client = _make_client(config)
    proj = config.get("project", {})
    target_words = proj.get("target_word_count", 200_000)
    platform = proj.get("target_platform", "web_serial_general")
    title = proj.get("title", "Untitled")
    auto_level = config.get("production", {}).get("automation_level", "guided")

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Project Profiler：分析项目画像...", total=None)
        agent = ProjectProfilerAgent(config, PROJECT_ROOT, client)
        profile = agent.generate_profile(idea, title, target_words, platform, auto_level, run_dir)
        p.update(t, description=f"[green]✅ 画像生成 — {profile.genre_primary} / {profile.length_class}[/green]")

    console.print(f"\n  题材: [cyan]{profile.genre_primary}[/cyan]")
    console.print(f"  长度级别: [cyan]{profile.length_class}[/cyan]")
    console.print(f"  章节卡策略: [cyan]{profile.production.chapter_card_policy}[/cyan]")
    console.print(f"  读者核心期待: {profile.reader_contract.core_expectation}")
    _save_cost("profile", client)


def run_stage_strategy(config: dict, state, run_dir: Path) -> None:
    """生成 Production_Strategy.yaml。"""
    from agents.production_strategy_agent import ProductionStrategyAgent
    from tools.ledger_registry import init_ledgers

    profile = load_profile()
    if profile is None:
        console.print("[yellow]⚠️  Project_Profile.yaml 不存在，使用配置文件推断...[/yellow]")
        from schemas.project_profile import ProjectProfile
        cfg_proj = config.get("project", {})
        profile = ProjectProfile(
            title=cfg_proj.get("title", ""),
            original_idea="",
            target_word_count=cfg_proj.get("target_word_count", 200_000),
            target_platform=cfg_proj.get("target_platform", ""),
            genre_primary=config.get("genre", {}).get("primary", "urban_rebirth"),
        )

    client = _make_client(config)
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Production Strategy Agent：生成生产策略...", total=None)
        agent = ProductionStrategyAgent(config, PROJECT_ROOT, client)
        strategy = agent.generate_strategy(profile, run_dir)
        p.update(t, description="[green]✅ 生产策略生成完成[/green]")

        t2 = p.add_task("Ledger Registry：初始化账本...", total=None)
        results = init_ledgers(PROJECT_ROOT, strategy.required_ledgers)
        created = sum(1 for s in results.values() if s == "created")
        p.update(t2, description=f"[green]✅ 账本初始化: {created} 个新建[/green]")

    console.print(f"\n  生产策略:")
    console.print(f"  - 长度模板: [cyan]{strategy.length_profile}[/cyan]")
    console.print(f"  - 题材模板: [cyan]{strategy.genre_profile}[/cyan]")
    console.print(f"  - 平台模板: [cyan]{strategy.platform_profile}[/cyan]")
    console.print(f"  - 目标章数: [cyan]{strategy.target_chapters}[/cyan]")
    console.print(f"  - 每章字数: [cyan]{strategy.words_per_chapter}[/cyan]")
    console.print(f"  - 批次大小: [cyan]{strategy.batch_policy.write_batch_size}[/cyan]")
    console.print(f"  - 章卡策略: [cyan]{strategy.chapter_card_policy.mode}[/cyan]")
    console.print(f"  - 必需账本: {', '.join(strategy.required_ledgers[:5])}{'...' if len(strategy.required_ledgers) > 5 else ''}")
    _save_cost("strategy", client)


def run_stage_cards(config: dict, state, run_dir: Path, start: int = 1, end: int = 0) -> None:
    """根据章节卡片策略生成章卡。"""
    from tools.parse_chapter_cards import parse_cards_with_llm

    strategy = load_strategy()
    profile = load_profile()
    if strategy is None:
        console.print("[yellow]⚠️  Production_Strategy.yaml 不存在，先运行 strategy 阶段[/yellow]")
        return

    mode = strategy.chapter_card_policy.mode
    target = strategy.target_chapters
    if end == 0:
        if mode == "full_preplan":
            end = target
        elif mode == "rolling_window":
            end = min(start + strategy.chapter_card_policy.rolling_window_size - 1, target)
        else:  # hybrid
            end = min(start + strategy.chapter_card_policy.hybrid_current_vol_detail - 1, target)

    client = _make_client(config)
    router = _make_router(config, client)
    pa = router.get_plot_architect()

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task(f"Plot Architect：生成第{start}-{end}章章纲...", total=None)
        if pa:
            pa.generate_chapter_outlines(start, end, run_dir)
        p.update(t, description="[green]✅ 章纲生成完成[/green]")

        t2 = p.add_task("解析为结构化 ChapterCard...", total=None)
        result = parse_cards_with_llm(PROJECT_ROOT, force=True)
        p.update(t2, description=f"[green]✅ {result[:60]}[/green]")

    console.print(f"\n  模式: {mode} | 范围: 第{start}-{end}章")
    _save_cost("cards", client)


def run_stage_produce(
    config: dict, state, batch: int = 5,
    until: int = 0, single_batch: bool = False
) -> None:
    """通用自适应生产循环——核心 v2 命令。"""
    from tools.produce_engine import ProduceEngine
    from tools.adaptive_quality_gate import run_adaptive_gate

    strategy = load_strategy()
    profile = load_profile()

    if strategy is None:
        console.print("[red]❌ Production_Strategy.yaml 不存在，请先运行 `python runner.py strategy`[/red]")
        sys.exit(1)
    if profile is None:
        console.print("[yellow]⚠️  Project_Profile.yaml 不存在，用配置推断...[/yellow]")
        from schemas.project_profile import ProjectProfile
        cfg_proj = config.get("project", {})
        profile = ProjectProfile(
            target_word_count=cfg_proj.get("target_word_count", 200_000),
            genre_primary=config.get("genre", {}).get("primary", "urban_rebirth"),
        )

    batch_size = batch or strategy.batch_policy.write_batch_size
    target_ch = until or strategy.target_chapters
    current_ch = state.current_chapter

    if current_ch >= target_ch:
        console.print(f"[green]✅ 已完成目标章节 {target_ch}，进入 export 阶段[/green]")
        return

    start_ch = current_ch + 1
    end_ch = min(start_ch + batch_size - 1, target_ch)

    console.print(Panel(
        f"[bold cyan]🔄 通用生产 第{start_ch}-{end_ch}章[/bold cyan]\n"
        f"策略: {strategy.length_profile} | {strategy.genre_profile} | {strategy.platform_profile}\n"
        f"进度: {current_ch}/{target_ch}章",
        expand=False
    ))

    client = _make_client(config)
    router = _make_router(config, client)
    run_dir = make_run_dir("produce")

    engine = ProduceEngine(PROJECT_ROOT, strategy, profile, state, router, console, run_dir)

    # 检查是否需要补充章卡（rolling_window 模式）
    if engine.should_rolling_refill(current_ch):
        console.print("  🔄 Rolling window：补充章卡...")
        msg = engine.do_rolling_refill(current_ch)
        console.print(f"  {msg[:80]}")

    # 执行写作批次
    result = engine.run_batch(start_ch, end_ch)

    if result["blocked"]:
        state.mark_failed("produce", result["block_reason"])
        save_state(state)
        _save_cost("produce", client)
        console.print(f"[red]❌ 生产阻断: {result['block_reason'][:120]}[/red]")
        sys.exit(1)

    written = result["written"]
    if not written:
        console.print("[yellow]⚠️  本批次未写出任何章节[/yellow]")
        return

    # 批次质量门
    gate = engine.run_post_batch_checks(written, end_ch)
    console.print(f"  质量门: {'🚨 阻断' if gate.blocked else '✅ 通过'}")
    if gate.blocked:
        state.quality_gate_failures.append(f"Ch{start_ch}-{end_ch}: {'; '.join(gate.block_reasons)}")
        save_state(state)
        _save_cost("produce", client)
        sys.exit(1)

    # 结构复盘
    if engine.should_do_structural_review(end_ch):
        console.print("  📋 结构复盘...")
        review = engine.do_structural_review(end_ch)
        console.print(f"  复盘完成 ({len(review)}字)")

    # 快照
    if engine.should_snapshot(end_ch):
        freeze_snapshot("produce", f"Ch{end_ch:04d}_PASS")

    # 更新状态
    words, chs = count_words()
    state.current_chapter = end_ch
    state.total_words = words
    save_state(state)
    _save_cost("produce", client)

    console.print(
        f"\n[green]✅ 批次完成[/green] 第{start_ch}-{end_ch}章 | "
        f"总字数: {words:,} | 进度: {end_ch}/{target_ch}章 ({100*end_ch//target_ch}%)"
    )

    if end_ch >= target_ch:
        console.print("\n[bold green]🎯 已达到目标章节数！运行 `python runner.py export` 导出。[/bold green]")


def run_stage_export(config: dict, state, run_dir: Path, force: bool = False) -> None:
    """自适应导出——根据 length_profile 决定导出产物。"""
    from tools import run_merge, run_export_docx, run_adaptive_gate, run_genre_promise_check

    strategy = load_strategy()
    profile = load_profile()

    requires_all_pass = config.get("quality_gates", {}).get("final_stage_requires_all_pass", True)
    if requires_all_pass and not force:
        gate = run_adaptive_gate(
            PROJECT_ROOT, run_dir, [], state.current_chapter,
            profile.length_class if profile else "volume_200k",
            profile.genre_primary if profile else "",
            strategy,
        )
        if gate.blocked:
            console.print(f"[red]❌ 质量门未通过，拒绝导出。使用 --force 强制跳过。[/red]")
            console.print(f"   阻断原因: {'; '.join(gate.block_reasons)}")
            sys.exit(1)

    artifacts = strategy.export_config.artifacts if strategy else ["final.md", "final.txt"]

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("合并全稿...", total=None)
        console.print(f"  {run_merge(PROJECT_ROOT)}")
        p.update(t, description="[green]✅ 全稿合并[/green]")

        if strategy and strategy.export_config.include_docx:
            t2 = p.add_task("导出 DOCX...", total=None)
            console.print(f"  {run_export_docx(PROJECT_ROOT)}")
            p.update(t2, description="[green]✅ DOCX 导出[/green]")

        if "chapter_index.md" in artifacts:
            t3 = p.add_task("生成章节索引...", total=None)
            _gen_chapter_index(run_dir)
            p.update(t3, description="[green]✅ 章节索引[/green]")

        if "unresolved_threads.md" in artifacts:
            t4 = p.add_task("汇总未解决线索...", total=None)
            _gen_unresolved(run_dir)
            p.update(t4, description="[green]✅ 未解决线索汇总[/green]")

        if any("synopsis" in a for a in artifacts):
            t5 = p.add_task("生成最终简介...", total=None)
            client = _make_client(config)
            router = _make_router(config, client)
            hook = router.get_commercial_hook()
            if hook:
                hook.generate_synopsis(run_dir)
            p.update(t5, description="[green]✅ 简介生成[/green]")

    words, chs = count_words()
    state.total_words = words
    save_state(state)

    console.print(f"\n[bold green]🎊 导出完成！总字数: {words:,}[/bold green]")
    console.print(f"  输出目录: [dim]{PROJECT_ROOT / 'project_repo/manuscript/final_export'}[/dim]")


# ── v1 兼容阶段（保留原有逻辑） ───────────────────────────────────────────────

def _run_v1_stage(target_stage: str, config: dict, state, batch: int) -> None:
    """兼容 v1 原有阶段逻辑。"""
    from schemas.state_schema import StageStatus

    run_dir = make_run_dir(target_stage)
    state.mark_started(target_stage, datetime.now().strftime("%Y%m%d_%H%M%S"))
    save_state(state)

    console.print(Panel(f"[bold cyan]{STAGE_LABELS.get(target_stage, target_stage)}[/bold cyan]", expand=False))

    try:
        if target_stage == "init":
            _v1_init(config, state, run_dir)
        elif target_stage == "concept":
            _v1_concept(config, state, run_dir)
        elif target_stage == "bible":
            _v1_bible(config, state, run_dir)
        elif target_stage == "outline":
            _v1_outline(config, state, run_dir)
        elif target_stage == "volume_001":
            _v1_volume001(config, state, run_dir)
        elif target_stage == "chapters":
            _v1_chapters(config, state, run_dir, batch)
            save_state(state)
            return
        elif target_stage == "revision":
            _v1_revision(config, state, run_dir)
        elif target_stage == "final":
            _v1_final(config, state, run_dir)

        snap = freeze_snapshot(target_stage, "PASS")
        state.mark_done(target_stage, str(snap))
        save_state(state)
        console.print(f"\n[green]✅ {target_stage} 完成[/green]")

    except Exception as e:
        freeze_snapshot(target_stage, "FAILED")
        state.mark_failed(target_stage, str(e))
        save_state(state)
        console.print(f"\n[red]❌ {target_stage} 失败: {e}[/red]")
        sys.exit(1)


def _v1_init(config, state, run_dir):
    from agents import GenreStrategistAgent, ShowrunnerAgent, RedTeamReviewerAgent
    client = _make_client(config)
    GenreStrategistAgent(config, PROJECT_ROOT, client).parse_user_idea(run_dir)
    GenreStrategistAgent(config, PROJECT_ROOT, client).analyze_genre(run_dir)
    ShowrunnerAgent(config, PROJECT_ROOT, client).audit_project(run_dir)
    RedTeamReviewerAgent(config, PROJECT_ROOT, client).review_concept(run_dir)
    _save_cost("init", client)


def _v1_concept(config, state, run_dir):
    from agents import CommercialHookAgent, ShowrunnerAgent
    client = _make_client(config)
    CommercialHookAgent(config, PROJECT_ROOT, client).generate_concept_package(run_dir)
    CommercialHookAgent(config, PROJECT_ROOT, client).generate_logline(run_dir)
    ShowrunnerAgent(config, PROJECT_ROOT, client).generate_direction("concept", run_dir)
    _save_cost("concept", client)


def _v1_bible(config, state, run_dir):
    from agents import CharacterKeeperAgent, WorldbuildingKeeperAgent, StyleKeeperAgent
    client = _make_client(config)
    router = _make_router(config, client)
    wb = router.get_worldbuilding_keeper()
    if wb:
        wb.build_world_bible(run_dir)
        wb.build_faction_map(run_dir)
        wb.build_timeline(run_dir)
        wb.build_relationship_map(run_dir)
    CharacterKeeperAgent(config, PROJECT_ROOT, client).build_character_bible(run_dir)
    if router.get_power_system_designer():
        router.get_power_system_designer().design_power_system(run_dir)
    sk = router.get_style_keeper()
    if sk:
        sk.build_voice_guide(run_dir)
    _save_cost("bible", client)


def _v1_outline(config, state, run_dir):
    from agents import PlotArchitectAgent, PromisePayoffValidatorAgent
    from tools import parse_cards_with_llm
    client = _make_client(config)
    opening_chapters = config.get("structure", {}).get("opening_chapters_detailed", 30)
    pa = PlotArchitectAgent(config, PROJECT_ROOT, client)
    pa.generate_full_outline(run_dir)
    pa.generate_volume_outlines(run_dir)
    pa.generate_chapter_outlines(1, opening_chapters, run_dir)
    pa.generate_ending_plan(run_dir)
    parse_cards_with_llm(PROJECT_ROOT)
    pv = PromisePayoffValidatorAgent(config, PROJECT_ROOT, client)
    fp = PROJECT_ROOT / "project_repo/outlines/03_full_outline.md"
    if fp.exists():
        pv.scan_new_promises(fp.read_text(encoding="utf-8"), 0, run_dir)
    _save_cost("outline", client)


def _v1_volume001(config, state, run_dir):
    from agents import ChapterWriterAgent, CommercialHookAgent, PromisePayoffValidatorAgent
    from schemas.chapter_card_schema import ChapterCard, ChapterCardIndex
    from tools import run_quality_gate
    client = _make_client(config)
    vol_dir = PROJECT_ROOT / "project_repo/manuscript/volume_001"
    vol_dir.mkdir(parents=True, exist_ok=True)
    card_path = PROJECT_ROOT / "project_repo/outlines/chapter_cards.yaml"
    idx = ChapterCardIndex(card_path if card_path.exists() else None)
    writer = ChapterWriterAgent(config, PROJECT_ROOT, client)
    written = []
    for ch_num in range(1, 11):
        card = idx.get(ch_num) or ChapterCard(chapter=ch_num)
        content = writer.write_chapter(ch_num, card, run_dir, vol_dir)
        written.append({"num": ch_num, "content": content, "title": card.title})
        state.current_chapter = ch_num
    CommercialHookAgent(config, PROJECT_ROOT, client).analyze_opening_hook(run_dir)
    gate = run_quality_gate(PROJECT_ROOT, run_dir, 10, config)
    if gate.blocked:
        raise RuntimeError(f"Quality Gate 阻断: {'; '.join(gate.block_reasons)}")
    state.total_words, _ = count_words()
    _save_cost("volume_001", client)


def _v1_chapters(config, state, run_dir, batch):
    from agents import ChapterWriterAgent, ContinuityCheckerAgent, PacingDoctorAgent, PromisePayoffValidatorAgent
    from schemas.chapter_card_schema import ChapterCard, ChapterCardIndex
    from tools import run_quality_gate

    current_ch = state.current_chapter
    start_ch = current_ch + 1
    end_ch = start_ch + batch - 1
    total_target = config.get("project", {}).get("target_chapter_count", 400)
    if start_ch > total_target:
        return
    end_ch = min(end_ch, total_target)

    client = _make_client(config)
    card_path = PROJECT_ROOT / "project_repo/outlines/chapter_cards.yaml"
    idx = ChapterCardIndex(card_path if card_path.exists() else None)
    writer = ChapterWriterAgent(config, PROJECT_ROOT, client)
    written = []
    volume_size = config.get("structure", {}).get("volume_size_chapters", 80)

    for ch_num in range(start_ch, end_ch + 1):
        vol_num = (ch_num - 1) // volume_size + 1
        vol_dir = PROJECT_ROOT / "project_repo/manuscript" / f"volume_{vol_num:03d}"
        vol_dir.mkdir(parents=True, exist_ok=True)
        card = idx.get(ch_num) or ChapterCard(chapter=ch_num)
        content = writer.write_chapter(ch_num, card, run_dir, vol_dir)
        written.append({"num": ch_num, "content": content, "title": card.title})
        state.current_chapter = ch_num

    ContinuityCheckerAgent(config, PROJECT_ROOT, client).check_batch(written, run_dir)
    PacingDoctorAgent(config, PROJECT_ROOT, client).check_batch_pacing(written, run_dir)
    pv = PromisePayoffValidatorAgent(config, PROJECT_ROOT, client)
    pv.scan_new_promises("\n\n".join(ch["content"] for ch in written), end_ch, run_dir)
    ContinuityCheckerAgent(config, PROJECT_ROOT, client).update_open_threads(run_dir)
    gate = run_quality_gate(PROJECT_ROOT, run_dir, end_ch, config)
    if gate.blocked:
        state.quality_gate_failures.append(f"Ch{start_ch}-{end_ch}: {'; '.join(gate.block_reasons)}")
        save_state(state)
        raise RuntimeError(f"Quality Gate 阻断: {'; '.join(gate.block_reasons)}")
    state.total_words, _ = count_words()
    _save_cost("chapters", client)


def _v1_revision(config, state, run_dir):
    import re as _re
    from agents import CharacterKeeperAgent, ContinuityCheckerAgent, PacingDoctorAgent, RedTeamReviewerAgent, StyleKeeperAgent
    client = _make_client(config)
    manuscript = PROJECT_ROOT / "project_repo/manuscript"
    chapters = []
    if manuscript.exists():
        for vol_dir in sorted(manuscript.iterdir()):
            if vol_dir.is_dir() and not vol_dir.name.startswith("final"):
                for ch_file in sorted(vol_dir.glob("ch*.md")):
                    m = _re.search(r"ch(\d+)", ch_file.stem)
                    if m:
                        chapters.append({"num": int(m.group(1)), "content": ch_file.read_text(encoding="utf-8")})
    recent = sorted(chapters, key=lambda x: x["num"])[-20:]
    sk = StyleKeeperAgent(config, PROJECT_ROOT, client)
    if recent:
        sk.check_style_consistency(recent[-10:], run_dir)
        PacingDoctorAgent(config, PROJECT_ROOT, client).check_batch_pacing(recent, run_dir)
        sample = "\n\n".join(ch["content"][:800] for ch in recent[:5])
        RedTeamReviewerAgent(config, PROJECT_ROOT, client).review_chapters(
            sample, f"{recent[0]['num']}-{recent[-1]['num']}", run_dir
        )
    CharacterKeeperAgent(config, PROJECT_ROOT, client).update_arc_tracker(
        f"当前章节：{state.current_chapter}", run_dir
    )
    ContinuityCheckerAgent(config, PROJECT_ROOT, client).update_open_threads(run_dir)
    _save_cost("revision", client)


def _v1_final(config, state, run_dir):
    from agents import CommercialHookAgent
    from tools import run_merge, run_export_docx, run_quality_gate
    client = _make_client(config)
    gate = run_quality_gate(PROJECT_ROOT, run_dir, state.current_chapter, config)
    if gate.blocked and config.get("quality_gates", {}).get("final_stage_requires_all_pass", True):
        raise RuntimeError(f"Final 质量门未通过: {'; '.join(gate.block_reasons)}")
    console.print(f"  {run_merge(PROJECT_ROOT)}")
    console.print(f"  {run_export_docx(PROJECT_ROOT)}")
    CommercialHookAgent(config, PROJECT_ROOT, client).generate_synopsis(run_dir)
    state.total_words, _ = count_words()
    _save_cost("final", client)


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _gen_chapter_index(run_dir: Path) -> None:
    manuscript = PROJECT_ROOT / "project_repo/manuscript"
    lines = ["# 章节索引\n", "| 章节 | 标题 | 字数 |", "|------|------|------|"]
    if manuscript.exists():
        for vol_dir in sorted(manuscript.iterdir()):
            if vol_dir.is_dir() and not vol_dir.name.startswith("final"):
                for ch_file in sorted(vol_dir.glob("ch*.md")):
                    m = re.search(r"ch(\d+)", ch_file.stem)
                    if m:
                        num = int(m.group(1))
                        content = ch_file.read_text(encoding="utf-8")
                        first_line = content.split("\n")[0].strip()
                        lines.append(f"| 第{num}章 | {first_line[:40]} | {len(content)} |")
    out = PROJECT_ROOT / "project_repo/manuscript/final_export/chapter_index.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def _gen_unresolved(run_dir: Path) -> None:
    src = PROJECT_ROOT / "project_repo/continuity/Open_Threads.md"
    dest = PROJECT_ROOT / "project_repo/manuscript/final_export/unresolved_threads.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dest)


# ── CLI ───────────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Web Novel OS v2 — 自适应长篇小说生产系统"""
    pass


@cli.command()
def init():
    """初始化项目（检查配置 + v1 init 阶段）"""
    config = load_config()
    state = load_state()
    core_idea = PROJECT_ROOT / "project_repo/outlines/00_core_idea.md"
    if not core_idea.exists() or len(core_idea.read_text(encoding="utf-8").strip()) < 50:
        console.print("[red]❌ 请先填写 project_repo/outlines/00_core_idea.md[/red]")
        sys.exit(1)
    _run_v1_stage("init", config, state, 5)


@cli.command()
def profile():
    """【v2】生成项目画像 Project_Profile.yaml"""
    config = load_config()
    state = load_state()
    run_dir = make_run_dir("profile")
    console.print(Panel("[bold cyan]📊 生成项目画像[/bold cyan]", expand=False))
    try:
        run_stage_profile(config, state, run_dir)
        snap = freeze_snapshot("profile", "PASS")
        state.mark_done("profile", str(snap))
        save_state(state)
        console.print("[green]✅ 项目画像生成完成[/green]")
    except Exception as e:
        freeze_snapshot("profile", "FAILED")
        state.mark_failed("profile", str(e))
        save_state(state)
        console.print(f"[red]❌ 失败: {e}[/red]")
        sys.exit(1)


@cli.command()
def strategy():
    """【v2】生成生产策略 Production_Strategy.yaml + 初始化账本"""
    config = load_config()
    state = load_state()
    run_dir = make_run_dir("strategy")
    console.print(Panel("[bold cyan]🗺️  生成生产策略[/bold cyan]", expand=False))
    try:
        run_stage_strategy(config, state, run_dir)
        snap = freeze_snapshot("strategy", "PASS")
        state.mark_done("strategy", str(snap))
        save_state(state)
        console.print("[green]✅ 生产策略生成完成[/green]")
    except Exception as e:
        freeze_snapshot("strategy", "FAILED")
        state.mark_failed("strategy", str(e))
        save_state(state)
        console.print(f"[red]❌ 失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--start", default=1, help="起始章节")
@click.option("--end", default=0, help="结束章节（0=自动按策略计算）")
def cards(start, end):
    """【v2】生成章节卡片（根据 strategy 的 chapter_card_policy）"""
    config = load_config()
    state = load_state()
    run_dir = make_run_dir("cards")
    console.print(Panel("[bold cyan]🃏 生成章节卡片[/bold cyan]", expand=False))
    try:
        run_stage_cards(config, state, run_dir, start, end)
        console.print("[green]✅ 章节卡片生成完成[/green]")
    except Exception as e:
        console.print(f"[red]❌ 失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--batch", default=0, help="每批章节数（0=使用策略配置）")
@click.option("--until", default=0, help="写到第几章（0=写到目标章节数）")
@click.option("--loop", is_flag=True, help="持续循环直到完成（每次完成一批后继续）")
def produce(batch, until, loop):
    """【v2】通用生产阶段——自适应批量写作"""
    config = load_config()
    state = load_state()

    if loop:
        strategy = load_strategy()
        target = until or (strategy.target_chapters if strategy else 400)
        while state.current_chapter < target:
            run_stage_produce(config, state, batch, until, single_batch=True)
            state = load_state()
            if state.current_chapter >= target:
                break
    else:
        run_stage_produce(config, state, batch, until, single_batch=True)


@cli.command()
@click.option("--force", is_flag=True, help="强制跳过质量门")
def export(force):
    """【v2】自适应导出"""
    config = load_config()
    state = load_state()
    run_dir = make_run_dir("export")
    console.print(Panel("[bold cyan]🎉 导出[/bold cyan]", expand=False))
    try:
        run_stage_export(config, state, run_dir, force)
        snap = freeze_snapshot("export", "PASS")
        state.mark_done("export", str(snap))
        save_state(state)
    except Exception as e:
        freeze_snapshot("export", "FAILED")
        state.mark_failed("export", str(e))
        save_state(state)
        console.print(f"[red]❌ 失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--stage", default=None, help="指定 v1 阶段")
@click.option("--auto", is_flag=True, help="全自动运行")
@click.option("--batch", default=5)
def run(stage, auto, batch):
    """运行 v1 兼容阶段"""
    config = load_config()
    state = load_state()

    if auto:
        for s in V1_STAGES:
            if not state.is_done(s):
                _run_v1_stage(s, config, state, batch)
        return

    target = stage or state.current_stage()
    if target == "done":
        console.print("[green]🎉 所有阶段已完成[/green]")
        return
    _run_v1_stage(target, config, state, batch)


@cli.command()
def status():
    """查看当前进度"""
    config = load_config()
    state = load_state()
    profile = load_profile()
    strategy = load_strategy()

    from schemas.state_schema import StageStatus

    table = Table(title="📊 项目进度", show_header=True)
    table.add_column("阶段")
    table.add_column("状态")
    table.add_column("运行次数")
    table.add_column("标签")

    all_stages = list(dict.fromkeys(V2_STAGES + V1_STAGES))
    for s in all_stages:
        rec = state.stages.get(s)
        if rec is None:
            continue
        icons = {
            StageStatus.DONE: "✅", StageStatus.FAILED: "❌",
            StageStatus.RUNNING: "▶️", StageStatus.PENDING: "⏳",
        }
        table.add_row(s, icons.get(rec.status, "?"), str(rec.run_count), STAGE_LABELS.get(s, s))

    console.print(table)

    words, chs = count_words()
    target_w = config.get("project", {}).get("target_word_count", 0)
    target_chs = strategy.target_chapters if strategy else config.get("project", {}).get("target_chapter_count", 0)

    console.print(f"\n字数: {words:,} / {target_w:,} ({100*words//max(target_w,1)}%)")
    console.print(f"章节: {chs} / {target_chs}")

    if profile:
        console.print(f"\n[bold]项目画像[/bold]")
        console.print(f"  题材: {profile.genre_primary} | 长度级别: {profile.length_class}")
        console.print(f"  章卡策略: {profile.production.chapter_card_policy}")
        console.print(f"  读者期待: {profile.reader_contract.core_expectation[:60]}")

    if strategy:
        console.print(f"\n[bold]生产策略[/bold]")
        console.print(f"  每批: {strategy.batch_policy.write_batch_size}章 | 复盘频率: 每{strategy.batch_policy.structural_review_every}章")
        console.print(f"  必需账本: {', '.join(strategy.required_ledgers[:5])}")

    if state.quality_gate_failures:
        console.print(f"\n[yellow]⚠️  质量门失败记录:[/yellow]")
        for f in state.quality_gate_failures[-3:]:
            console.print(f"  - {f}")


@cli.command()
@click.option("--chapter", default=0)
def check(chapter):
    """运行校验工具"""
    from tools import (
        run_word_budget_check, run_pacing_check, run_hook_check,
        run_promise_check, run_continuity_check, run_character_check,
        run_genre_promise_check, report_ledger_status,
    )

    state = load_state()
    config = load_config()
    current_ch = chapter or state.current_chapter
    reports_dir = PROJECT_ROOT / "runs" / "CHECK_REPORTS"
    reports_dir.mkdir(parents=True, exist_ok=True)

    checks = [
        ("字数预算",   lambda: run_word_budget_check(PROJECT_ROOT)),
        ("节奏检查",   lambda: run_pacing_check(PROJECT_ROOT, config)),
        ("钩子质量",   lambda: run_hook_check(PROJECT_ROOT)),
        ("承诺-回报",  lambda: run_promise_check(PROJECT_ROOT, current_ch)),
        ("类型承诺",   lambda: run_genre_promise_check(PROJECT_ROOT, current_ch)),
        ("连续性",    lambda: run_continuity_check(PROJECT_ROOT)),
        ("人物一致性", lambda: run_character_check(PROJECT_ROOT)),
        ("账本状态",   lambda: report_ledger_status(PROJECT_ROOT)),
    ]

    console.print(Panel("[bold cyan]🔍 运行校验工具[/bold cyan]", expand=False))
    for name, fn in checks:
        try:
            result = fn()
            (reports_dir / f"{name}.md").write_text(result, encoding="utf-8")
            first_issue = next((l for l in result.split("\n") if any(s in l for s in ["⚠️", "❌", "🚨"])), None)
            if first_issue:
                console.print(f"  [yellow]⚠️  {name}[/yellow]: {first_issue.strip()[:80]}")
            else:
                console.print(f"  [green]✅ {name}[/green]")
        except Exception as e:
            console.print(f"  [red]❌ {name}: {e}[/red]")

    console.print(f"\n报告: [dim]{reports_dir}[/dim]")


@cli.command()
def snapshot():
    """手动快照"""
    state = load_state()
    snap = freeze_snapshot(state.current_stage(), "MANUAL")
    console.print(f"[green]✅ 快照:[/green] {snap.name}")


@cli.command()
@click.option("--snapshot", "snap_name", default=None)
def rollback(snap_name):
    """回滚到快照"""
    snaps_dir = PROJECT_ROOT / "snapshots"
    if not snaps_dir.exists():
        console.print("[red]❌ 没有快照[/red]")
        sys.exit(1)
    snaps = sorted(snaps_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
    if not snap_name:
        console.print("[bold]可用快照:[/bold]")
        for i, s in enumerate(snaps):
            console.print(f"  {i+1:2d}. {s.name}")
        console.print("\n使用: python runner.py rollback --snapshot <名称>")
        return
    target = snaps_dir / snap_name
    if not target.exists():
        partial = [s for s in snaps if snap_name in s.name]
        if len(partial) == 1:
            target = partial[0]
        else:
            console.print(f"[red]❌ 快照不存在: {snap_name}[/red]")
            sys.exit(1)
    console.print(f"[yellow]⚠️  回滚到: {target.name}，是否继续？[y/N] [/yellow]", end="")
    if input().strip().lower() != "y":
        return
    repo = PROJECT_ROOT / "project_repo"
    backup = PROJECT_ROOT / f"project_repo_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copytree(repo, backup)
    shutil.rmtree(repo)
    shutil.copytree(target, repo)
    console.print(f"[green]✅ 已回滚到: {target.name}[/green]")


@cli.command()
def cost():
    """查看 API 成本"""
    if not COST_LOG_PATH.exists():
        console.print("暂无成本记录")
        return
    with open(COST_LOG_PATH, encoding="utf-8") as f:
        records = json.load(f)
    table = Table(title="💰 API 成本")
    table.add_column("阶段")
    table.add_column("调用")
    table.add_column("输入Token")
    table.add_column("输出Token")
    table.add_column("成本USD")
    table.add_column("时间")
    total = 0.0
    for r in records:
        table.add_row(
            r.get("stage","?"), str(r.get("call_count",0)),
            f"{r.get('total_input_tokens',0):,}", f"{r.get('total_output_tokens',0):,}",
            f"${r.get('total_cost_usd',0):.4f}", r.get("timestamp","?")[:19],
        )
        total += r.get("total_cost_usd", 0)
    console.print(table)
    console.print(f"\n[bold]总计: ${total:.4f} USD[/bold]")


if __name__ == "__main__":
    cli()
