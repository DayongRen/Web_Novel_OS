# 100k Milestone Review

Use this protocol to keep long novels from drifting or looping after large context growth.

## Principle

Every 100k words/characters, stop drafting and rebuild the operating view of the novel.

The next 100k block should not be a blind continuation. It should begin from:

1. what has actually been written
2. how that compares to the original architecture
3. what reader promises are open or overdue
4. what patterns have repeated
5. what the next block must change

## Trigger

Run when total manuscript size crosses:

```text
100k, 200k, 300k, ...
```

Use:

```bash
python .codex/skills/novel-compiler-pro/scripts/build_milestone_report.py --write-report
```

The script creates a mechanical block map. The agent must then add semantic analysis.

## Required Files

Update:

```text
reports/milestone_100k_report.md
memory/rolling_100k_state.md
planning/rolling_100k_plan.md
memory/repetition_guard.md
memory/open_threads.md
canon/timeline.md
canon/foreshadowing.md
```

## Review Steps

### 1. Summarize Completed Block

For the completed 100k block, record:

- chapters included
- main events
- relationship changes
- character arc movement
- world/canon additions
- promises opened
- promises paid off
- unresolved questions
- repeated scene patterns

### 2. Compare Against Architecture

Read summary-level architecture:

```text
planning/book_plan.md
planning/plot_spine.md
planning/part_plan.md
planning/volume_plan.md
planning/chapter_plan.md
planning/scene_plan.md
```

Compare:

- planned state vs actual state
- planned reveal timing vs actual reveal timing
- planned relationship arc vs actual movement
- planned volume objective vs actual progress
- promised payoff timing vs actual status
- repeated patterns that were not in the plan

### 3. Decide Drift Handling

For each drift:

- accept into canon
- repair recent chapters
- re-plan the next block
- mark `[建议人工复核]` if it changes a hard constraint

Do not silently continue after major drift.

### 4. Reopen The Next 100k Block

Before writing the next block, produce:

```text
planning/rolling_100k_plan.md
memory/rolling_100k_state.md
memory/next_chapter_task.md
```

The next block brief must include:

- block objective
- expected chapters
- key state changes
- required payoffs
- new pressures
- forbidden repeats from prior block
- planned midpoint shift inside the block
- block ending state

## Continuing Generation

Only continue drafting when:

1. the current block has a summary
2. architecture comparison is written
3. next block plan exists
4. high-severity repetition or continuity problems are repaired or explicitly deferred
5. `memory/repetition_guard.md` lists forbidden repeats for the next block

This creates a long-form rhythm:

```text
write up to 100k
  -> summarize actual text
  -> compare to architecture
  -> repair or accept drift
  -> re-plan next 100k
  -> write next block
```
