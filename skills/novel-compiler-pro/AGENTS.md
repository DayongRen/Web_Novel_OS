# AGENTS.md

This folder contains the `novel-compiler-pro` Skill package.

The live novel project state belongs in the user's project root, not inside this Skill package.

Default project workflow:

```text
constitution -> specify -> clarify -> canon build -> planning -> tasks -> write -> gates -> repair -> analyze -> final assembly
```

Default structural hierarchy:

```text
Book -> Part -> Volume -> Chapter -> Scene
```

Chapter filenames must follow:

```text
全局编号_部_卷_卷标题_章节名.txt
```

Example:

```text
0021_第一部_卷三_盲海回声_第五章 观测站.txt
```

Keep `SKILL.md` concise. Put detailed protocol material in `references/`.

For user-facing invocation examples and setup notes, update `USAGE.md`.

## Scripts

No-dependency Python scripts live in `scripts/`.

Use them from a novel project root:

```bash
python .codex/skills/novel-compiler-pro/scripts/check_project.py --write-report
python .codex/skills/novel-compiler-pro/scripts/check_chapters.py --write-report
python .codex/skills/novel-compiler-pro/scripts/check_scene_density.py --write-report
python .codex/skills/novel-compiler-pro/scripts/check_repetition.py --write-report
python .codex/skills/novel-compiler-pro/scripts/word_count.py --write-report
python .codex/skills/novel-compiler-pro/scripts/build_retrieval_index.py
python .codex/skills/novel-compiler-pro/scripts/build_milestone_report.py --write-report
python .codex/skills/novel-compiler-pro/scripts/assemble_final.py --write-report
```
