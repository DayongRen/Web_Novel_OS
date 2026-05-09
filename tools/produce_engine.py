"""
tools/produce_engine.py — 通用生产引擎

读取 Production_Strategy.yaml，执行自适应的批量写作循环。
替换原来固定的 volume_001 + chapters 两个阶段。

核心原则：
1. 禁止缺章卡就用空卡继续
2. 禁止固定"写前10章"逻辑
3. 禁止固定"一卷20万"逻辑
4. 完全由 strategy 驱动批次大小、复盘频率、质量门
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from schemas.chapter_card_schema import ChapterCard, ChapterCardIndex
from schemas.production_strategy import ProductionStrategy
from schemas.project_profile import ProjectProfile
from schemas.state_schema import ProjectState


class ProduceEngine:
    def __init__(
        self,
        project_root: Path,
        strategy: ProductionStrategy,
        profile: ProjectProfile,
        state: ProjectState,
        router,            # AgentRouter
        console=None,
        run_dir: Optional[Path] = None,
    ):
        self.root = project_root
        self.strategy = strategy
        self.profile = profile
        self.state = state
        self.router = router
        self.run_dir = run_dir or project_root / "runs" / "produce"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        from rich.console import Console
        self.console = console or Console()

    # ── 主生产循环 ────────────────────────────────────────────────────────────

    def run_batch(self, start_ch: int, end_ch: int) -> dict:
        """
        写 start_ch..end_ch 章节。
        返回 {"written": [...], "blocked": bool, "block_reason": str}
        """
        card_idx = self._load_card_index()
        result = {"written": [], "blocked": False, "block_reason": ""}

        writer = self.router.get_chapter_writer()
        if writer is None:
            raise RuntimeError("ChapterWriterAgent 未激活")

        for ch_num in range(start_ch, end_ch + 1):
            if ch_num > self.strategy.target_chapters:
                self.console.print(f"  已达目标章节 {self.strategy.target_chapters}，停止")
                break

            card = card_idx.get(ch_num)
            if card is None:
                # 严格模式：缺章卡必须修复大纲，不能继续
                msg = (
                    f"❌ 第{ch_num}章缺少 ChapterCard，"
                    f"当前 chapter_card_policy={self.strategy.chapter_card_policy.mode}。"
                    f"\n请先运行 `python runner.py outline` 或 `python runner.py cards --start {ch_num}` 生成章卡。"
                )
                result["blocked"] = True
                result["block_reason"] = msg
                self.console.print(f"[red]{msg}[/red]")
                self._save_block_report(ch_num, msg)
                return result

            vol_dir = self._get_vol_dir(ch_num)

            try:
                content = writer.write_chapter(ch_num, card, self.run_dir, vol_dir)
            except Exception as e:
                action = self.strategy.failure_policy.generation_exception
                if action == "retry_same_chapter":
                    max_r = self.strategy.failure_policy.max_retries
                    for attempt in range(1, max_r):
                        self.console.print(f"  ↩️  第{ch_num}章重试 {attempt}/{max_r-1}...")
                        try:
                            content = writer.write_chapter(ch_num, card, self.run_dir, vol_dir)
                            break
                        except Exception:
                            if attempt == max_r - 1:
                                raise
                else:
                    raise

            result["written"].append({"num": ch_num, "content": content, "title": card.title})
            self.state.current_chapter = ch_num
            self.console.print(f"  ✅ 第{ch_num}章 ({len(content)}字)")

            # 每章后提取 Canon Delta
            if self._should_extract_canon():
                self._extract_canon(ch_num, content)

            # 每章后扫描 Promise
            self._scan_promises_single(ch_num, content)

        return result

    def run_post_batch_checks(self, written: list[dict], batch_end_ch: int) -> "AdaptiveGateReport":
        """批次结束后运行所有质量门。"""
        from tools.adaptive_quality_gate import run_adaptive_gate
        gate = run_adaptive_gate(
            project_root=self.root,
            run_dir=self.run_dir,
            chapters=written,
            current_chapter=batch_end_ch,
            length_class=self.profile.length_class,
            genre=self.profile.genre_primary,
            strategy=self.strategy,
        )
        return gate

    def should_do_structural_review(self, current_ch: int) -> bool:
        interval = self.strategy.batch_policy.structural_review_every
        return current_ch > 0 and current_ch % interval == 0

    def should_do_major_reoutline(self, current_ch: int) -> bool:
        interval = self.strategy.batch_policy.major_reoutline_every
        return (
            interval < 999
            and current_ch > 0
            and current_ch % interval == 0
        )

    def should_snapshot(self, current_ch: int) -> bool:
        interval = self.strategy.batch_policy.snapshot_every
        return current_ch > 0 and current_ch % interval == 0

    def should_rolling_refill(self, current_ch: int) -> bool:
        """rolling_window 模式：判断是否需要补充章卡。"""
        if self.strategy.chapter_card_policy.mode != "rolling_window":
            return False
        window = self.strategy.chapter_card_policy.rolling_window_size
        card_idx = self._load_card_index()
        look_ahead = current_ch + self.strategy.batch_policy.write_batch_size
        return not card_idx.has(look_ahead) and look_ahead <= self.strategy.target_chapters

    def do_structural_review(self, current_ch: int) -> str:
        """运行结构复盘，返回报告文本。"""
        from agents import PlotArchitectAgent
        pa = self.router.get_plot_architect()
        if pa is None:
            return "PlotArchitectAgent 未激活"

        context = pa._build_base_context(layer="volume")
        prompt = f"""
当前章节：第{current_ch}章
目标章节：{self.strategy.target_chapters}章
完成进度：{current_ch/self.strategy.target_chapters:.0%}

请对当前进度进行结构复盘：
1. 主线是否按计划推进？偏离了多少？
2. 读者期待（{self.profile.reader_contract.core_expectation}）是否在被满足？
3. 当前卷目标完成状态？
4. 接下来{self.strategy.batch_policy.structural_review_every}章的重点是什么？
5. 是否需要修改后续章纲？（是/否 + 原因）

输出：Markdown，中文，简洁。
"""
        result = pa.call_llm(prompt, temperature=0.4)
        out = self.run_dir / f"Structural_Review_Ch{current_ch:04d}.md"
        out.write_text(result, encoding="utf-8")
        return result

    def do_rolling_refill(self, current_ch: int) -> str:
        """rolling_window 模式：补充未来章卡。"""
        from tools.parse_chapter_cards import parse_cards_with_llm
        window = self.strategy.chapter_card_policy.rolling_window_size
        start = current_ch + 1
        end = min(start + window - 1, self.strategy.target_chapters)

        pa = self.router.get_plot_architect()
        if pa is None:
            return "PlotArchitectAgent 未激活"

        pa.generate_chapter_outlines(start, end, self.run_dir)
        result = parse_cards_with_llm(self.root, force=True)
        return f"Rolling 补充章卡 {start}-{end}：{result}"

    # ── 辅助方法 ──────────────────────────────────────────────────────────────

    def _load_card_index(self) -> ChapterCardIndex:
        card_path = self.root / "project_repo/outlines/chapter_cards.yaml"
        return ChapterCardIndex(card_path if card_path.exists() else None)

    def _get_vol_dir(self, ch_num: int) -> Path:
        vol_size = max(20, self.strategy.target_chapters // 5)
        vol_num = (ch_num - 1) // vol_size + 1
        vol_dir = self.root / "project_repo/manuscript" / f"volume_{vol_num:03d}"
        vol_dir.mkdir(parents=True, exist_ok=True)
        return vol_dir

    def _should_extract_canon(self) -> bool:
        cfg = self.root / "novel_config.yaml"
        if cfg.exists():
            with open(cfg, encoding="utf-8") as f:
                c = yaml.safe_load(f) or {}
            return c.get("continuity", {}).get("auto_extract_canon_delta", True)
        return True

    def _extract_canon(self, ch_num: int, content: str) -> None:
        try:
            from tools.extract_canon_delta import run_extract_canon_delta
            run_extract_canon_delta(self.root, ch_num, content, self.run_dir, auto_apply=True)
        except Exception:
            pass

    def _scan_promises_single(self, ch_num: int, content: str) -> None:
        try:
            pp = self.router.get_promise_validator()
            if pp:
                pp.scan_new_promises(content, ch_num, self.run_dir)
        except Exception:
            pass

    def _save_block_report(self, ch_num: int, msg: str) -> None:
        report = self.run_dir / "Block_Report.md"
        report.write_text(
            f"# 生产阻断报告\n\n**阻断位置**: 第{ch_num}章\n\n**原因**:\n{msg}\n\n"
            f"**恢复方式**:\n```bash\npython runner.py cards --start {ch_num}\npython runner.py produce\n```",
            encoding="utf-8",
        )

    def count_manuscript_words(self) -> int:
        total = 0
        manuscript = self.root / "project_repo/manuscript"
        if manuscript.exists():
            for f in manuscript.rglob("ch*.md"):
                total += len(f.read_text(encoding="utf-8"))
        return total
