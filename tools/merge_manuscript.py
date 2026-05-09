"""
merge_manuscript.py — 合并全稿工具
将所有分章 .md 文件按顺序合并为 novel_full.md 和 novel_full.txt。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def collect_chapters(project_root: Path) -> list[dict]:
    manuscript = project_root / "project_repo/manuscript"
    chapters = []
    if not manuscript.exists():
        return chapters
    for vol_dir in sorted(manuscript.iterdir()):
        if vol_dir.is_dir() and not vol_dir.name.startswith("final"):
            for ch_file in sorted(vol_dir.glob("ch*.md")):
                m = re.search(r"ch(\d+)", ch_file.stem)
                if m:
                    chapters.append({
                        "num": int(m.group(1)),
                        "volume": vol_dir.name,
                        "path": ch_file,
                        "content": ch_file.read_text(encoding="utf-8"),
                    })
    return sorted(chapters, key=lambda x: x["num"])


def merge_to_markdown(chapters: list[dict], project_root: Path) -> Path:
    export_dir = project_root / "project_repo/manuscript/final_export"
    export_dir.mkdir(parents=True, exist_ok=True)

    parts = []
    current_vol = None
    for ch in chapters:
        if ch["volume"] != current_vol:
            current_vol = ch["volume"]
            vol_label = current_vol.replace("volume_", "第").replace("_", "") + "卷"
            vol_summary_path = project_root / "project_repo/manuscript" / current_vol / "volume_summary.md"
            if vol_summary_path.exists():
                summary = vol_summary_path.read_text(encoding="utf-8")
                parts.append(f"\n\n---\n\n# {vol_label}\n\n{summary}\n\n---\n")
            else:
                parts.append(f"\n\n---\n\n# {vol_label}\n\n---\n")
        parts.append(ch["content"])

    full_text = "\n\n".join(parts)
    out_md = export_dir / "novel_full.md"
    out_md.write_text(full_text, encoding="utf-8")
    return out_md


def merge_to_txt(chapters: list[dict], project_root: Path) -> Path:
    export_dir = project_root / "project_repo/manuscript/final_export"
    export_dir.mkdir(parents=True, exist_ok=True)

    parts = []
    for ch in chapters:
        content = ch["content"]
        content = re.sub(r"#+\s+", "", content)
        content = re.sub(r"\*\*(.+?)\*\*", r"\1", content)
        content = re.sub(r"\*(.+?)\*", r"\1", content)
        parts.append(content)

    full_text = "\n\n".join(parts)
    out_txt = export_dir / "novel_full.txt"
    out_txt.write_text(full_text, encoding="utf-8")
    return out_txt


def run_merge(project_root: Path) -> str:
    chapters = collect_chapters(project_root)
    if not chapters:
        return "❌ 未找到任何章节文件。"

    total_words = sum(len(ch["content"]) for ch in chapters)

    out_md = merge_to_markdown(chapters, project_root)
    out_txt = merge_to_txt(chapters, project_root)

    return (
        f"✅ 合并完成\n"
        f"- 章节数: {len(chapters)}\n"
        f"- 总字数: {total_words:,}\n"
        f"- Markdown: {out_md}\n"
        f"- TXT: {out_txt}"
    )


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print(run_merge(root))
