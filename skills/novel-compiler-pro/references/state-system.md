# Smart State And Long-Term Memory

Use this file to maintain continuity across long projects.

## Purpose

`memory/` is not canon. It is the active operating state of the writing engine.

Use memory to prevent long-running drift:

- what just happened
- what is currently active
- what should happen next
- what style to maintain
- what promises readers are waiting on
- what unresolved threads must not be forgotten

Canon stores authoritative facts. Memory stores working context and retrieval hints.

## Core Files

### `memory/smart_state.md`

The top-level session restore file.

Must contain:

- active project title
- current compile stage
- current part/volume/chapter
- last completed chapter
- next planned chapter
- active protagonist state
- active relationship changes
- active foreshadowing items
- current reader expectation
- high-risk continuity notes
- next actions

### `memory/novel_state.md`

The larger project state.

Must contain:

- total planned scale
- completed chapter count
- current word count estimate
- current arc status
- open arcs
- closed arcs
- recent major changes
- active constraints

### `memory/recent_chapter_summaries.md`

Keep compact summaries for the last 3-10 chapters.

Each entry:

```markdown
## 0021 第五章 观测站

- 事件：
- 人物状态：
- 信息变化：
- 伏笔变化：
- 读者期待：
- 下一章压力：
```

### `memory/next_chapter_task.md`

Write the immediate next chapter task.

Include:

- target filename
- chapter function
- scene list
- must include
- must avoid
- canon files to check
- reader hook
- ending pressure

### `memory/style_anchor.md`

Maintain living style anchors:

- viewpoint
- narrative distance
- sentence density
- dialogue traits
- description density
- emotional expression mode
- forbidden expressions
- sample cadence

Do not paste long copyrighted reference text. Use short abstracted style notes.

### `memory/reader_promise.md`

Track why readers continue:

- surface hook
- emotional promise
- curiosity engine
- power/fantasy promise if applicable
- relationship promise
- mystery promise
- platform fit notes

### `memory/open_threads.md`

Track unresolved questions and story debts:

```markdown
| ID | Thread | Opened At | Type | Expected Payoff | Urgency | Status |
|---|---|---|---|---|---|---|
```

Statuses:

```text
未开启
已开启
推进中
待回收
已回收
建议弱化
疑似遗忘
```

### `memory/repetition_guard.md`

The anti-copy-paste state file.

Maintain:

- recent 5 chapter scene functions
- recent 5 opening patterns
- recent 5 ending hook types
- repeated motions, images, sentence habits, and dialogue moves
- what the next chapter must not repeat
- the exact state increment required before drafting

Before drafting, read this file and answer:

```text
What changes in this chapter that was not true before?
What recent pattern must this chapter avoid?
What new pressure, cost, decision, or information does the chapter add?
```

If the answers are vague, repair `planning/chapter_plan.md` or `planning/scene_plan.md` before drafting.

### `memory/rolling_100k_state.md`

The current 100k-word block state.

Maintain:

- block number and target range
- chapters included in the current block
- estimated current word/character count
- current block objective
- previous block summary
- architecture comparison notes
- next block replan trigger

When a 100k boundary is reached, update this file before continuing.

### `memory/retrieval_index.md`

A lightweight retrieval map when no script/RAG system exists.

Use it to map characters, events, places, and terms to chapters.

```markdown
| Keyword | Type | Related Chapters | Notes |
|---|---|---|---|
```

Build or refresh it with:

```bash
python .codex/skills/novel-compiler-pro/scripts/build_retrieval_index.py
```

The script also writes optional chapter metadata to:

```text
memory/retrieval/chapter_meta/*.meta.json
```

This is a lightweight retrieval layer, not a vector database. Upgrade to true RAG only after the manuscript grows large enough that simple indexing stops being useful.

## Update Rules

After each chapter:

1. Update `memory/smart_state.md`.
2. Append/update `memory/recent_chapter_summaries.md`.
3. Update `memory/next_chapter_task.md`.
4. Update `memory/open_threads.md`.
5. Update `memory/retrieval_index.md` if new searchable entities appear.
6. Update canon for authoritative changes.

After each batch:

1. Compress old chapter summaries.
2. Keep only the newest 3-10 detailed summaries.
3. Move durable facts into canon.
4. Move closed local state out of Smart State.

## Context Loading Rule

Before drafting a chapter, load only the files that matter:

- `memory/smart_state.md`
- `memory/novel_state.md`
- `memory/style_anchor.md`
- `memory/next_chapter_task.md`
- `memory/repetition_guard.md`
- `memory/rolling_100k_state.md`
- relevant canon files
- relevant chapter and scene plan

Avoid rereading the whole manuscript unless the task is a global audit.
