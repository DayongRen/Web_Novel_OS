# Quality Gates

Use these gates after each chapter, each batch, and before final assembly.

## Scripted Gate Layer

Run the mechanical gate scripts before semantic review whenever possible:

```bash
python .codex/skills/novel-compiler-pro/scripts/check_project.py --write-report
python .codex/skills/novel-compiler-pro/scripts/check_chapters.py --write-report
python .codex/skills/novel-compiler-pro/scripts/check_scene_density.py --write-report
python .codex/skills/novel-compiler-pro/scripts/check_repetition.py --write-report
python .codex/skills/novel-compiler-pro/scripts/word_count.py --write-report
```

Script outputs:

- `reports/project_gate_report.md`
- `reports/chapter_gate_report.md`
- `reports/scene_density_report.md`
- `reports/repetition_report.md`
- `reports/word_count_report.md`

Scripts can detect missing structure, invalid filenames, numbering gaps, duplicate chapter numbers, rough word counts, and obvious draft residue. After scripts pass or warn, perform the semantic checks below.
Repetition gates catch exact and near-structural repetition; they do not replace semantic anti-repetition review.
Scene-density gates catch summary-like prose, missing early dialogue, banned AI-style phrases, and conclusion-like endings; they do not replace the Anti-AI Rewriter pass.

## Chapter Gate

Run after every drafted chapter.

Check:

1. Chapter function is fulfilled.
2. Chapter belongs to the correct part and volume.
3. There is a clear goal or pressure.
4. There is resistance, cost, or conflict.
5. At least one state changes.
6. At least one character makes or responds to a meaningful choice.
7. Information flow is plausible.
8. No character knows impossible information.
9. Canon is not contradicted.
10. Timeline is plausible.
11. Foreshadowing is updated.
12. Reader has a reason to continue.
13. No meta notes, TODOs, or outline residue remain in prose.
14. The chapter is scene-driven rather than summary-driven.
15. The chapter avoids banned AI-style explanatory patterns.
16. The chapter has enough visible action, dialogue, objects, and spatial movement.

Write result to `reports/compile_log.md`.

If high severity appears, repair before continuing.

## Batch Consistency Gate

Run every 3-5 chapters or after each volume.

Write `reports/consistency_report.md`.

Also run `scripts/check_repetition.py --write-report` after every batch. If it returns `FAIL`, repair repeated text or repeated scene function before drafting more chapters.
Also run `scripts/check_scene_density.py --write-report`. If it returns `FAIL`, rewrite through the Anti-AI Rewriter before continuing.

Issue table:

```markdown
| ID | Type | Severity | Location | Problem | Evidence | Suggested Fix | Status |
|---|---|---|---|---|---|---|---|
```

Severity:

- `高`: breaks main plot, character credibility, world rules, timeline, or reader comprehension.
- `中`: harms pacing, emotional continuity, setup/payoff, clarity, or scene function.
- `低`: local wording, repetition, minor naming/style issue.

## Consistency Categories

### Timeline

- event order
- travel time
- injury/recovery time
- simultaneous presence
- cause before effect

### Character Knowledge

- who knows what
- when they learned it
- how information traveled
- what they should not know

### Character Motivation

- desire
- fear
- current pressure
- relationship state
- cost of choice
- established bottom line

### World Rules

- hard rules
- resource limits
- power/technology/magic/medical rules
- institutional logic
- taboos

### Terminology

- names
- titles
- organizations
- places
- technical terms
- relationship address terms

### Foreshadowing

- setup count
- escalation
- false leads
- payoff timing
- lost threads

### Chapter Function

- duplicate function
- low-conflict run
- pure explanation
- delayed story movement
- overlong transition

### Repetition

- repeated passage across chapters
- same opening image or sentence form
- same ending hook type without escalation
- repeated scene sequence such as investigate -> blocked -> tiny clue
- repeated emotional beat without new cost
- repeated stock phrase or body action

### Scene Mode / Anti-AI Style

- first paragraph lacks concrete image or action
- no dialogue appears in the first 500 Chinese characters
- long stretches contain no visible event
- direct emotional labels replace behavior
- banned commentary patterns appear
- chapter ends with abstract summary instead of image/action/dialogue
- dialogue explains plot like a briefing

## Repair Pass

Write `reports/revision_report.md`.

Prefer small repairs:

- add a motivation sentence
- add an action beat
- add an information source
- add a time transition
- reorder paragraphs
- cut repetitive exposition
- soften over-strong foreshadowing
- add a light setup earlier
- revise dialogue tone
- sharpen ending hook

Avoid large repairs unless unavoidable:

- do not casually change event outcomes
- do not delete major characters
- do not change the ending direction
- do not add major world rules
- do not reorder a whole volume
- do not change core personality

Repair record:

```markdown
## Repair ID: R-0001

- Source issue:
- Changed file:
- Location:
- Method:
- Reason:
- Downstream impact:
- Human review needed:
```

## Style Gate

Write `reports/style_report.md`.

Check:

- viewpoint consistency
- narrative distance
- character voice
- term/title consistency
- sentence density
- dialogue naturalness
- explanation-heavy paragraphs
- over-literary embellishment
- modern/classical register mismatch
- repeated phrase patterns
- AI-flavored generic cadence

Do not change plot during style repair.

## Final Gate

Write `reports/final_consistency_report.md`.

Before final semantic review, run:

```bash
python .codex/skills/novel-compiler-pro/scripts/check_project.py --write-report
python .codex/skills/novel-compiler-pro/scripts/check_chapters.py --write-report
python .codex/skills/novel-compiler-pro/scripts/check_scene_density.py --write-report
python .codex/skills/novel-compiler-pro/scripts/check_repetition.py --write-report
python .codex/skills/novel-compiler-pro/scripts/build_retrieval_index.py
python .codex/skills/novel-compiler-pro/scripts/build_milestone_report.py --write-report
python .codex/skills/novel-compiler-pro/scripts/assemble_final.py --write-report
```

Check:

1. All planned chapters exist.
2. Global numbers are continuous or gaps are documented.
3. Part/volume/chapter hierarchy is correct.
4. Canon agrees with manuscript.
5. Timeline is complete.
6. Major character states are clear.
7. Major foreshadowing states are clear.
8. No high-severity issue remains unresolved without explanation.
9. Terminology and titles are unified.
10. Ending answers the main conflict.
11. No duplicate or broken chapters.
12. No key branch is left unintentionally open.
13. No unrecorded major setting appears.

If high severity remains, return to repair before final assembly.
