# File Templates

Use these templates when initializing missing files.

## `specs/constitution.md`

```markdown
# Constitution

## Creative Principles

## Target Reader

## Target Platform

## Genre And Subgenre

## Emotional Promise

## Narrative Viewpoint

## Style Boundary

## Hard Constraints

## Forbidden Content

## Automation Level

## Chapter Length Range

## Ending Direction

## Human Review Needed
```

## `specs/specification.md`

```markdown
# Specification

## Title

## One-Sentence Story

## Protagonist

## Main Conflict

## Core Secret

## World Rules

## Major Characters

## Major Relationships

## Expected Structure

## Must-Have Events

## Forbidden Events

## Final State
```

## `planning/chapter_plan.md`

```markdown
# Chapter Plan

## 0001_第一部_卷一_卷标题_第一章 章标题

### Structure

- Global number:
- Part:
- Volume:
- Volume title:
- Chapter:

### Chapter Function

### Chapter Goal

### POV

### Characters

### Location

### Time

### Opening State

### Core Conflict

### Event Progress

### Information Reveal

### Character Change

### Reader Hook

### Emotional Payoff

### New Foreshadowing

### Foreshadowing Payoff

### Ending Pressure

### Must Include

### Must Avoid

### Target Word Count

### Previous Chapter Link

### Next Chapter Link
```

## `planning/scene_plan.md`

```markdown
# Scene Plan

## 0001_第一部_卷一_卷标题_第一章 章标题

### Scene 1

- Function:
- Characters:
- Location:
- Conflict:
- New information:
- Emotional shift:
- Opening image:
- Key action:
- Ending action:
- Reader hook:
- Link to next scene:
- Must include:
- Must avoid:
```

## `canon/foreshadowing.md`

```markdown
# Foreshadowing

| ID | Foreshadowing | First Setup | Related Character/Object/Event | Expected Payoff | Current Status | Handling Note |
|---|---|---|---|---|---|---|
```

Allowed statuses:

```text
未埋设
已埋设
部分回收
已回收
疑似丢失
建议弱化
建议删除
```

## `reports/final_report.md`

```markdown
# Final Report

## Project Summary

## Total Word Count

## Total Chapters

## Part / Volume / Chapter Structure

## Major Characters

## Major Locations

## Major Organizations

## World Rules Summary

## Foreshadowing Status

## Completed Revisions

## High-Severity Issue Handling

## Remaining Medium/Low Issues

## Human Review Suggestions

## File List
```

## `memory/repetition_guard.md`

```markdown
# Repetition Guard

## Recent Context Loading Rule

- Load summaries and canon first.
- Load at most the latest 1-2 full chapters unless doing an audit.
- Never paste a large old chapter block as style fuel.

## Recent 5 Chapters: Scene Functions Used

## Recent 5 Chapters: Opening Patterns Used

## Recent 5 Chapters: Ending Hooks Used

## Recent 5 Chapters: Repeated Motions / Images / Phrases

## Do Not Repeat Next

## Next Chapter Required State Increment

- World state:
- Character state:
- Relationship state:
- Information state:
- Reader expectation:
```

## `memory/rolling_100k_state.md`

```markdown
# Rolling 100k State

## Current Block

- Block number:
- Target range:
- Current word/char estimate:
- Start chapter:
- Latest chapter:

## Previous Block Summary

## Current Block Must Accomplish

## Current Block Must Not Repeat

## Architecture Comparison Notes

## Next Block Replan Trigger
```

## `planning/rolling_100k_plan.md`

```markdown
# Rolling 100k Plan

## Whole-Book Architecture Snapshot

## Completed Blocks

## Current 100k Block Plan

## Difference From Original Architecture

## Next 100k Block Plan

## Risks Before Continuing
```

## `reports/repetition_report.md`

```markdown
# Repetition Report

| ID | Severity | Type | Location | Problem | Evidence | Suggested Fix | Status |
|---|---|---|---|---|---|---|---|
```

## `reports/scene_density_report.md`

```markdown
# Scene Density Report

| ID | Severity | Type | Location | Problem | Evidence | Suggested Fix | Status |
|---|---|---|---|---|---|---|---|
```

## `reports/anti_ai_style_report.md`

```markdown
# Anti-AI Style Report

## Summary

## Banned Sentence Patterns

## Abstract Emotion Labels

## Summary-Like Paragraphs

## Required Rewrites
```

## `reports/milestone_100k_report.md`

```markdown
# 100k Milestone Report

## Current Block Map

## What Has Happened

## Architecture Comparison

## Drift / Repetition Risks

## Next 100k Generation Brief
```
