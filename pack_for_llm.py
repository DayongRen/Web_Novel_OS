#!/usr/bin/env python3
"""
pack_for_llm.py — 将整个 Web Novel OS 项目打包成单个文本文件，供大模型阅读。

用法：
  python pack_for_llm.py                    # 输出到 project_overview.md
  python pack_for_llm.py --out review.txt   # 自定义输出文件名
  python pack_for_llm.py --no-content       # 只输出文件树，不含文件内容
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).parent

# 包含的扩展名
INCLUDE_EXTS = {".py", ".yaml", ".yml", ".md", ".txt"}

# 跳过的目录/文件
SKIP_DIRS = {
    ".git", "__pycache__", ".env", "node_modules",
    "snapshots", "runs",          # 运行时产物
    "final_export",               # 导出文件
}
SKIP_FILES = {
    "project_overview.md",        # 避免自引用
    "pack_for_llm.py",            # 自身
    ".env",
}


def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return path.name in SKIP_FILES


def collect_files(root: Path) -> list[Path]:
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix in INCLUDE_EXTS and not should_skip(p):
            files.append(p)
    return files


def build_tree(files: list[Path], root: Path) -> str:
    lines = [f"{root.name}/"]
    seen_dirs: set[Path] = set()
    for f in files:
        rel = f.relative_to(root)
        parts = rel.parts
        for i in range(len(parts) - 1):
            d = Path(*parts[:i+1])
            if d not in seen_dirs:
                indent = "  " * i + "├── "
                lines.append(f"{indent}{parts[i]}/")
                seen_dirs.add(d)
        indent = "  " * (len(parts) - 1) + "└── "
        lines.append(f"{indent}{parts[-1]}")
    return "\n".join(lines)


def build_document(files: list[Path], root: Path, include_content: bool) -> str:
    parts: list[str] = []

    parts.append("# Web Novel OS v1.0 — 完整项目文档\n")
    parts.append("> 此文件由 pack_for_llm.py 自动生成，包含项目中所有源代码和配置文件。\n")
    parts.append(f"> 文件总数：{len(files)}\n")
    parts.append("---\n")

    parts.append("## 项目文件树\n")
    parts.append("```")
    parts.append(build_tree(files, root))
    parts.append("```\n")
    parts.append("---\n")

    if not include_content:
        return "\n".join(parts)

    parts.append("## 文件内容\n")

    for f in files:
        rel = str(f.relative_to(root))
        ext = f.suffix.lstrip(".")
        lang = {"py": "python", "yaml": "yaml", "yml": "yaml", "md": "markdown", "txt": "text"}.get(ext, "text")
        content = f.read_text(encoding="utf-8", errors="replace")

        parts.append(f"### `{rel}`\n")
        parts.append(f"```{lang}")
        parts.append(content.rstrip())
        parts.append("```\n")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Pack Web Novel OS project for LLM review")
    parser.add_argument("--out", default="project_overview.md", help="输出文件名")
    parser.add_argument("--no-content", action="store_true", help="只输出文件树")
    args = parser.parse_args()

    files = collect_files(ROOT)
    doc = build_document(files, ROOT, include_content=not args.no_content)

    out_path = ROOT / args.out
    out_path.write_text(doc, encoding="utf-8")

    size_kb = out_path.stat().st_size // 1024
    # rough token estimate: ~1 token per 3.5 chars for Chinese+code mixed
    char_count = len(doc)
    token_estimate = char_count // 3

    print(f"✅ 已生成: {out_path}")
    print(f"   文件数: {len(files)}")
    print(f"   大小:   {size_kb} KB")
    print(f"   字符数: {char_count:,}")
    print(f"   预估Token: ~{token_estimate:,}")
    print()
    print("📋 使用方式：")
    print(f"   直接将 {args.out} 的内容粘贴到目标大模型的对话框中，")
    print(f"   然后提问：'请仔细阅读这个项目，提出你认为有问题或不足的地方。'")


if __name__ == "__main__":
    main()
