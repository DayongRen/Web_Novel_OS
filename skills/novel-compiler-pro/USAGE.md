# Novel Compiler Pro Usage

这是 `novel-compiler-pro` 的使用说明。全局 Skill 名称是：

```text
novel
```

在 Codex 对话里优先用：

```text
使用 $novel，继续这个小说项目。
```

或：

```text
用 novel skill，扫描当前项目并继续写后续章节。
```

## 什么时候会自动生效

如果当前项目根目录有 `AGENTS.md`，并且里面指定默认使用 `.codex/skills/novel-compiler-pro/SKILL.md`，你可以直接说：

```text
继续写下一批章节。
```

跨电脑、跨项目或新对话里，建议显式写 `$novel`，这样最稳。

## 常用对话命令

### 新项目初始化

```text
使用 $novel，初始化一个新的中文长篇小说项目，按 novel-compiler-pro 的目录结构创建 input、memory、canon、specs、planning、manuscript、reports、final。
```

### 只规划，不写正文

```text
使用 $novel，只执行到 scene_plan。读取 input/，建立 specs、canon、book_plan、volume_plan、chapter_plan 和 scene_plan，不生成正文。
```

### 完整自动编译

```text
使用 $novel，按 autonomous compile mode 编译整部小说。先读取 input/，建立 canon 和 planning，再生成章节正文，运行门禁，修复问题，最后合并 final/final_novel.md。
```

### 基于已有章节续写

```text
使用 $novel，扫描 manuscript/chapters/ 下已有章节，更新 memory、canon 和 timeline，然后从下一章开始续写 3-5 章。不要推翻已有正文。
```

### 修订已有小说

```text
使用 $novel，进入修订模式。先运行一致性、重复、场景密度和字数门禁，再按报告修复逻辑、人物动机、时间线、伏笔和文风问题。不要直接重写全书。
```

### 专门去 AI 味

```text
使用 $novel 的 Anti-AI Rewriter，修订第 39 章，把总结式段落改成场景化叙事。保留剧情事实、人物关系、canon、timeline 和章节功能。
```

### 运行门禁检查

```text
使用 $novel，运行项目门禁、章节门禁、场景密度门禁、重复检查、10w 里程碑检查和字数统计，并告诉我哪些问题需要优先修。
```

## 标准项目目录

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

正文章节文件必须放在：

```text
manuscript/chapters/
```

命名格式必须是：

```text
全局编号_部_卷_卷标题_章节名.txt
```

示例：

```text
0021_第一部_卷三_盲海回声_第五章 观测站.txt
```

## 常用脚本

从小说项目根目录运行：

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

其中 `check_scene_density.py` 会检查总结式写法、AI 味禁用句式、前 500 字对话、可见事件密度和总结式结尾。

## 换电脑使用

推荐方式：

```text
使用 skill-installer，从 https://github.com/DayongRen/Web_Novel_OS 安装 skills/novel-compiler-pro 到全局 skills。
```

手动方式：

1. 下载或克隆 GitHub 仓库。
2. 把 `skills/novel-compiler-pro/` 复制到：

```text
%USERPROFILE%\.codex\skills\novel-compiler-pro
```

3. 重启 Codex。
4. 在对话中使用：

```text
使用 $novel，继续这个小说项目。
```

## 最小输入文件

如果你要让它自动编译，至少建议准备：

```text
input/project_brief.md
input/world_seed.md
input/character_seed.md
input/plot_seed.md
input/style_seed.md
input/constraints.md
```

信息不完整时，Skill 会保守推断，并把需要人工复核的地方写进 `canon/unresolved_questions.md` 和 `reports/compile_log.md`。
