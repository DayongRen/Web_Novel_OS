#!/usr/bin/env python3
"""Validate the novel-compiler-pro project skeleton."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    OPTIONAL_DIRS,
    REQUIRED_DIRS,
    REQUIRED_FILES,
    exit_code_for_status,
    markdown_table,
    print_json,
    root_path,
    status_from_issues,
    write_text,
)


def build_report(root: Path) -> dict:
    issues = []
    dirs = []
    files = []

    for rel in REQUIRED_DIRS:
        path = root / rel
        exists = path.is_dir()
        dirs.append({"path": rel, "exists": exists, "required": True})
        if not exists:
            issues.append({"severity": "高", "type": "missing_dir", "path": rel, "message": "Required directory is missing."})

    for rel in OPTIONAL_DIRS:
        dirs.append({"path": rel, "exists": (root / rel).is_dir(), "required": False})

    for directory, names in REQUIRED_FILES.items():
        for name in names:
            rel = f"{directory}/{name}"
            exists = (root / rel).is_file()
            files.append({"path": rel, "exists": exists})
            if not exists:
                issues.append({"severity": "中", "type": "missing_file", "path": rel, "message": "Required template or state file is missing."})

    if not (root / "AGENTS.md").is_file():
        issues.append({"severity": "中", "type": "missing_file", "path": "AGENTS.md", "message": "Project agent protocol is missing."})

    status = status_from_issues(issues)
    return {
        "status": status,
        "root": str(root),
        "directories": dirs,
        "files": files,
        "issues": issues,
        "summary": {
            "required_dirs": len(REQUIRED_DIRS),
            "missing_required_dirs": sum(1 for item in dirs if item["required"] and not item["exists"]),
            "required_files": sum(len(names) for names in REQUIRED_FILES.values()),
            "missing_required_files": sum(1 for item in files if not item["exists"]),
        },
    }


def to_markdown(report: dict) -> str:
    issue_rows = [
        [idx + 1, issue["severity"], issue["type"], issue["path"], issue["message"]]
        for idx, issue in enumerate(report["issues"])
    ]
    if not issue_rows:
        issue_rows = [["-", "-", "-", "-", "No structural issues found."]]

    dir_rows = [
        [item["path"], "required" if item["required"] else "optional", "yes" if item["exists"] else "no"]
        for item in report["directories"]
    ]

    return "\n\n".join(
        [
            "# Project Gate Report",
            f"- Status: {report['status']}",
            f"- Root: `{report['root']}`",
            "## Summary",
            markdown_table(
                ["Required Dirs", "Missing Dirs", "Required Files", "Missing Files"],
                [[
                    report["summary"]["required_dirs"],
                    report["summary"]["missing_required_dirs"],
                    report["summary"]["required_files"],
                    report["summary"]["missing_required_files"],
                ]],
            ),
            "## Directories",
            markdown_table(["Path", "Kind", "Exists"], dir_rows),
            "## Issues",
            markdown_table(["#", "Severity", "Type", "Path", "Message"], issue_rows),
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Novel project root. Defaults to current directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--write-report", nargs="?", const="reports/project_gate_report.md", help="Write Markdown report to path.")
    args = parser.parse_args()

    report = build_report(root_path(args.root))
    if args.json:
        print_json(report)
    else:
        output = to_markdown(report)
        print(output)
        if args.write_report:
            write_text(root_path(args.root) / args.write_report, output)
    return exit_code_for_status(report["status"])


if __name__ == "__main__":
    raise SystemExit(main())
