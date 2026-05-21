# Workflow

Use this workflow to compile a Chinese long-form novel from materials into final manuscript.

## SDD + Novel Compile Flow

```text
constitution
  -> specify
  -> clarify
  -> canon build
  -> book/part/volume plan
  -> chapter/scene plan
  -> tasks
  -> write
  -> update memory/canon
  -> quality gates
  -> anti-repetition gate
  -> 100k milestone review when due
  -> repair
  -> analyze
  -> final assembly
```

## 0. Initialize

Create missing directories and seed files listed in `project-structure.md`.

Initialize `canon/naming_rules.md` with the chapter filename law.

Initialize `reports/compile_log.md` with:

- current date
- detected input files
- detected existing manuscript files
- missing required files
- assumptions marked `[建议人工复核]`

Then run:

```bash
python .codex/skills/novel-compiler-pro/scripts/check_project.py --write-report
```

## 1. Constitution

Write `specs/constitution.md`.

It defines the creative constitution:

- target reader and platform if known
- genre and emotional promise
- narrative viewpoint and style boundary
- hard constraints and forbidden content
- automation level
- chapter length range
- ending direction
- non-negotiable story principles

If unknown, use conservative defaults and mark `[建议人工复核]`.

## 2. Specify

Write `specs/specification.md` as the story PRD:

- title
- one-sentence premise
- protagonist
- main conflict
- core secret
- world rules
- major characters
- major relationship tensions
- expected part/volume scale
- final state
- reader promise
- must-have events
- forbidden events

## 3. Clarify

Write `specs/clarifications.md`.

Do not ask the user unless blocked. Instead:

- list ambiguities
- choose conservative defaults
- note impact
- mark risky assumptions `[建议人工复核]`

Ask only for critical blockers named in `SKILL.md`.

## 4. Canon Build

Build `canon/` from `input/`, `specs/`, existing manuscript, and current planning.

Canon is the authority over:

- world
- characters
- timeline
- locations
- organizations
- terminology
- relationships
- foreshadowing
- style

Any new detail introduced later must update canon.

## 5. Planning

Build plans in order:

```text
planning/premise.md
planning/theme.md
planning/book_plan.md
planning/plot_spine.md
planning/part_plan.md
planning/volume_plan.md
planning/chapter_plan.md
planning/scene_plan.md
```

Planning law:

- Book carries final thematic and plot transformation.
- Part carries a large-stage state change.
- Volume carries a clear phase objective and phase conflict.
- Chapter carries an action, choice, relationship change, or information change.
- Scene carries conflict, reveal, emotion shift, or action progress.

No purely decorative chapter is allowed.

## 6. Tasks

Write `specs/tasks.md`.

Break the next compile batch into executable tasks:

- chapter files to draft or repair
- canon updates required
- memory updates required
- gates to run
- expected output files

For ongoing writing, default to 3-5 chapters per batch.

## 7. Write

Draft from canon and plans, not from free invention.

For each chapter:

1. Read relevant canon.
2. Read `memory/smart_state.md`, `memory/novel_state.md`, `memory/style_anchor.md`, and `memory/next_chapter_task.md`.
3. Read the chapter and scene plan.
4. Draft prose to `manuscript/chapters/`.
5. Update memory and canon.
6. Run mechanical gates:
   ```bash
   python .codex/skills/novel-compiler-pro/scripts/check_chapters.py --write-report
   python .codex/skills/novel-compiler-pro/scripts/check_repetition.py --write-report
   python .codex/skills/novel-compiler-pro/scripts/word_count.py --write-report
   python .codex/skills/novel-compiler-pro/scripts/build_retrieval_index.py
   ```
7. Update `memory/repetition_guard.md` with recent patterns and the next required state increment.
8. Run semantic gates.

## 7.5 Anti-Repetition Pass

Use [anti-repetition.md](anti-repetition.md) before and after each batch.

Before drafting:

- load summaries, canon, active plans, and at most the latest 1-2 full chapters
- require a concrete state increment
- list what recent pattern must not repeat

After drafting:

- run `scripts/check_repetition.py --write-report`
- repair exact repeated passages immediately
- update `memory/repetition_guard.md`

Do not continue a long generation run when the repetition gate fails.

## 7.6 100k Milestone Review

Use [milestone-100k.md](milestone-100k.md) whenever the manuscript crosses a 100k-word/character block boundary.

Run:

```bash
python .codex/skills/novel-compiler-pro/scripts/build_milestone_report.py --write-report
```

Then write or update:

```text
reports/milestone_100k_report.md
memory/rolling_100k_state.md
planning/rolling_100k_plan.md
```

Before starting the next 100k block:

1. summarize what has happened in the completed block
2. compare the block against `planning/book_plan.md`, `plot_spine.md`, `part_plan.md`, and `volume_plan.md`
3. identify drift, repeated patterns, delayed promises, and missing state changes
4. re-read the whole architecture at summary level, not by loading all prose
5. generate the next 100k block brief
6. update chapter/scene plans for the next block

## 8. Analyze

Write `specs/analysis.md` and relevant reports after each batch.

Analyze:

- what changed
- what risks remain
- whether reader promise is still being delivered
- whether chapter functions are distinct
- whether major setups and payoffs are moving

## 9. Final Assembly

Before assembly, run final consistency.

Then sort chapter files by global number and create:

```text
final/final_novel.md
reports/final_report.md
```

Use the assembly script:

```bash
python .codex/skills/novel-compiler-pro/scripts/check_repetition.py --write-report
python .codex/skills/novel-compiler-pro/scripts/build_milestone_report.py --write-report
python .codex/skills/novel-compiler-pro/scripts/assemble_final.py --write-report
```

Final manuscript format:

```markdown
# 小说标题

# 第一部：部标题

## 卷一：卷标题

### 第一章 章标题

正文……
```
