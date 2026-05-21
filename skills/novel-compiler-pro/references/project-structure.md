# Project Structure

Use this file when initializing or repairing a novel project.

## Root Layout

Create these folders at the user's novel project root:

```text
input/
memory/
canon/
specs/
planning/
manuscript/
manuscript/chapters/
reports/
final/
market/
```

`market/` is optional and should be used only when the user wants platform analysis, trend analysis, comparable-book deconstruction, or commercial web-novel positioning.

## Directory Roles

| Directory | Role | Source |
|---|---|---|
| `input/` | Raw user-provided materials and seeds | User |
| `specs/` | SDD-style creative requirements and decisions | wordflowlab-inspired |
| `memory/` | Smart State, recent summaries, progress, active task, style anchor | leenbj-inspired |
| `canon/` | Authoritative story facts and continuity tables | novel-compiler core |
| `planning/` | Book/part/volume/chapter/scene plans | novel-compiler core |
| `manuscript/chapters/` | Draft chapter files | novel-compiler core |
| `reports/` | Compile logs, gates, repairs, pacing, style, final reports | shared |
| `final/` | Assembled manuscript | novel-compiler core |
| `market/` | Optional platform, reader, benchmark, trope, and deconstruction notes | oh-story-inspired |

## Required Seed Files

Create these when missing:

```text
input/project_brief.md
input/world_seed.md
input/character_seed.md
input/plot_seed.md
input/style_seed.md
input/constraints.md
input/reference_fragments.md
```

Never overwrite populated user input files. If a file exists, append only when the task requires it.

## Required Specs Files

```text
specs/constitution.md
specs/specification.md
specs/clarifications.md
specs/creative_plan.md
specs/tasks.md
specs/analysis.md
```

## Required Memory Files

```text
memory/smart_state.md
memory/novel_state.md
memory/recent_chapter_summaries.md
memory/next_chapter_task.md
memory/style_anchor.md
memory/reader_promise.md
memory/open_threads.md
memory/retrieval_index.md
memory/repetition_guard.md
memory/rolling_100k_state.md
```

## Required Canon Files

```text
canon/world.md
canon/characters.md
canon/timeline.md
canon/locations.md
canon/organizations.md
canon/terminology.md
canon/relationship_map.md
canon/foreshadowing.md
canon/unresolved_questions.md
canon/style_guide.md
canon/naming_rules.md
```

## Required Planning Files

```text
planning/premise.md
planning/theme.md
planning/book_plan.md
planning/plot_spine.md
planning/part_plan.md
planning/volume_plan.md
planning/chapter_plan.md
planning/scene_plan.md
planning/rolling_100k_plan.md
```

## Required Reports

```text
reports/compile_log.md
reports/consistency_report.md
reports/character_arc_report.md
reports/foreshadowing_report.md
reports/pacing_report.md
reports/revision_report.md
reports/style_report.md
reports/repetition_report.md
reports/milestone_100k_report.md
reports/final_consistency_report.md
reports/final_report.md
```

## Chapter Filename Parser

Parse chapter filenames by underscores:

```text
0001_第一部_卷一_卷标题_第一章 章标题.txt
```

Fields:

1. global chapter number
2. part name
3. volume name
4. volume title
5. chapter title

If existing files do not match, record proposed migration in `reports/compile_log.md` before renaming.
