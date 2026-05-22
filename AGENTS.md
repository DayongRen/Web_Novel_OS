# AGENTS.md

本项目是中文长篇小说编译项目。默认使用：

`.codex/skills/novel-compiler-pro/SKILL.md`

旧版 `.codex/skills/novel-compiler/SKILL.md` 仅作为历史原型保留，不作为默认流程。

## 核心目标

本项目不是简单辅助写作，也不是只做扫榜或局部续写。

默认目标是：根据 `input/` 下的核心资料，按规格驱动、设定驱动、规划优先的方式，将长篇小说自动编译为完整项目稿。

## 对话中使用

本 Skill 的短名是：

```text
novel
```

在任意 Codex 对话中可以显式触发：

```text
使用 $novel，继续这个小说项目。
```

常用示例：

```text
使用 $novel，只执行到 scene_plan，不生成正文。
使用 $novel，扫描 manuscript/chapters/ 下已有章节，然后续写 3-5 章。
使用 $novel 的 Anti-AI Rewriter，修订第 39 章，把总结式段落改成场景化叙事。
使用 $novel，运行项目门禁、章节门禁、场景密度门禁、重复检查、10w 里程碑检查和字数统计。
```

完整使用说明见：

```text
.codex/skills/novel-compiler-pro/USAGE.md
```

## 默认结构

```text
Book -> Part -> Volume -> Chapter -> Scene
```

中文对应：

```text
全书 -> 部 -> 卷 -> 章 -> 场景
```

## 默认流程

```text
constitution
  -> specify
  -> clarify
  -> canon build
  -> book/part/volume planning
  -> chapter/scene planning
  -> tasks
  -> write
  -> update memory/canon
  -> quality gates
  -> repair
  -> analyze
  -> final assembly
```

除非用户明确要求只诊断、只规划、只修订或只写某一章，否则按 `novel-compiler-pro` autonomous compile mode 推进。

## 项目目录

```text
input/       原始核心资料
memory/      Smart State 与长期写作记忆
canon/       权威设定库
specs/       SDD 风格规格文件
planning/    部/卷/章/场景规划
manuscript/  正文草稿
reports/     检查、修复、节奏、风格和最终报告
final/       最终合并稿
market/      可选：读者、平台、拆文和商业化检查
```

## 正文命名规则

正文文件必须使用：

```text
全局编号_部_卷_卷标题_章节名.txt
```

示例：

```text
0021_第一部_卷三_盲海回声_第五章 观测站.txt
```

排序以四位全局章节编号为准。

## 工作守则

- 不直接从一句 prompt 写长篇正文；先建立 `specs/`、`canon/`、`planning/`。
- `canon/` 是事实中枢；新增人物、地点、组织、术语、规则、伏笔必须登记。
- `memory/` 是运行状态；每章后更新 Smart State、最近章节摘要、下一章任务和开放线索。
- 每章必须有目标、阻力、变化和继续阅读理由。
- 每 3-5 章或每卷执行 batch consistency check，并优先运行脚本化门禁。
- 发现高严重度问题时先修复，再继续生成后文。
- 最终稿合并到 `final/final_novel.md`，最终报告写入 `reports/final_report.md`。

## 脚本化门禁

从项目根目录运行：

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

脚本负责结构、命名、编号、字数、草稿残留、场景密度、重复片段、轻量检索索引、10w 里程碑和最终合并。语义一致性、人物动机、伏笔回收和读者体验仍由 `novel-compiler-pro` 按报告继续判断。
