# Anti-Repetition Guard

Use this protocol to prevent long-form copy-paste drift.

## Three-Layer Guard

### 1. Context Hygiene

Do not load the whole manuscript before drafting a new chapter.

Load in this order:

1. `memory/smart_state.md`
2. `memory/recent_chapter_summaries.md`
3. `memory/repetition_guard.md`
4. `memory/next_chapter_task.md`
5. relevant canon files
6. relevant chapter and scene plans
7. at most the latest 1-2 full chapters if needed for immediate continuity

Use older chapters through summaries, canon, `memory/retrieval_index.md`, or targeted search. Do not paste large old prose blocks as style reference.

### 2. State Increment Requirement

Before drafting, answer in `memory/repetition_guard.md`:

```text
This chapter changes:
- world state:
- character state:
- relationship state:
- information state:
- reader expectation:
```

At least one item must be concrete and irreversible. Good increments include:

- a relationship gains or loses trust
- a secret moves from unknown to suspected
- a faction changes tactics
- a resource is spent or lost
- a promise opens, escalates, or pays off
- a character chooses a costlier path

If the increment is only "continues investigation", "deepens atmosphere", or "adds worldbuilding", repair the plan before writing.

### 3. Scripted Repetition Gate

Run after each chapter or batch:

```bash
python .codex/skills/novel-compiler-pro/scripts/check_repetition.py --write-report
```

It writes:

```text
reports/repetition_report.md
```

If the script reports `FAIL`, repair before writing more.

## Patterns To Track

Record recent use in `memory/repetition_guard.md`:

- opening image
- opening sentence shape
- ending hook type
- scene function sequence
- repeated body action
- repeated weather/light image
- repeated dialogue move
- repeated internal realization
- repeated investigation loop
- repeated conflict resolution

## Repair Rules

Prefer structural repair over synonym replacement.

Allowed repairs:

- change scene objective
- change information source
- change obstacle type
- change who acts first
- change cost of success
- move a reveal forward or backward
- replace a repeated opening with a concrete new situation
- replace repeated introspection with action or dialogue
- cut copied paragraphs

Weak repairs:

- only swapping adjectives
- only changing names
- only changing weather
- adding a sentence while keeping the same scene function

## Anti-Repetition Chapter Prompt

Before drafting each chapter, silently check:

```text
The last chapters already used:
- opening:
- scene loop:
- hook:
- emotional beat:
- stock phrases:

This chapter must avoid:

This chapter's new state increment is:
```

If this cannot be filled, do not draft yet.
