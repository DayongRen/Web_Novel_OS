# Web Novel OS v1.0 + Novel Studio

一个面向长篇网文、短篇爽文、类型文、定制题材的自动迭代式小说生产系统。  
包含命令行引擎（`runner.py`）和可视化工作台（Novel Studio）。

## 一句话定义

Web Novel OS 是一个以类型范本为导航、以人物和世界观为约束、以分卷分章为状态机、以多 Agent 协作为执行方式、以节奏/爽点/伏笔/一致性校验为护栏的网络小说创作操作系统。

## 快速开始

### Studio 模式（推荐）

```bash
pip install -r requirements.txt
pip install fastapi uvicorn[standard] python-multipart
cp .env.example .env   # 填入 ANTHROPIC_API_KEY
python start_studio.py
# 浏览器打开 http://localhost:8765
```

### 命令行模式

```bash
cp .env.example .env
vim project_repo/outlines/00_core_idea.md  # 填写创意
python runner.py init
python runner.py run --auto   # 全自动
python runner.py status
python runner.py check
python runner.py rollback
python runner.py cost
```



```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 Anthropic API Key
```

### 3. 填写小说创意

编辑 `project_repo/outlines/00_core_idea.md`，写入你的小说想法。

### 4. 配置项目参数

编辑 `novel_config.yaml`，设置类型、目标字数、平台等。

### 5. 运行系统

```bash
# 初始化项目（分析类型、评估风险）
python runner.py init

# 生成概念包（书名、简介、卖点）
python runner.py run --stage concept

# 构建故事圣经（世界观、人物、力量体系）
python runner.py run --stage bible

# 生成总纲和前30章细纲
python runner.py run --stage outline

# 生成第一卷完整章纲和前10章正文
python runner.py run --stage volume_001

# 批量写章节（每批5章）
python runner.py run --stage chapters

# 修订（节奏、人设、文风）
python runner.py run --stage revision

# 最终输出（合并全文、导出）
python runner.py run --stage final

# 全自动运行所有阶段
python runner.py run --auto
```

## 目录结构

```
Web_Novel_OS/
├── runner.py                   # 主入口
├── novel_config.yaml           # 项目配置
├── system_prompt.md            # 系统主提示词
├── requirements.txt
├── .env.example
│
├── agents/                     # 14个专业Agent
│   ├── base_agent.py
│   ├── showrunner.py
│   ├── genre_strategist.py
│   ├── plot_architect.py
│   ├── character_keeper.py
│   ├── worldbuilding_keeper.py
│   ├── power_system_designer.py
│   ├── chapter_writer.py
│   ├── dialogue_agent.py
│   ├── pacing_doctor.py
│   ├── promise_payoff_validator.py
│   ├── continuity_checker.py
│   ├── style_keeper.py
│   ├── commercial_hook_agent.py
│   └── red_team_reviewer.py
│
├── tools/                      # 校验与处理工具
│   ├── check_continuity.py
│   ├── check_character_consistency.py
│   ├── check_promise_payoff.py
│   ├── check_pacing.py
│   ├── check_chapter_hooks.py
│   ├── check_word_budget.py
│   ├── merge_manuscript.py
│   └── export_docx.py
│
├── project_repo/               # 小说唯一真源
│   ├── manuscript/
│   ├── outlines/
│   ├── canon/
│   ├── continuity/
│   ├── style/
│   └── market/
│
├── templates/                  # 类型范本库
│   ├── genre_profiles/
│   ├── beat_sheets/
│   ├── micro_templates/
│   └── reference_patterns/
│
├── runs/                       # 每轮运行记录
└── snapshots/                  # 冻结快照
```

## 支持的类型

| 类型 | 配置文件 |
|------|---------|
| 玄幻升级文 | `xuanhuan_upgrade.yaml` |
| 都市重生文 | `urban_rebirth.yaml` |
| 仙侠宗门文 | `xianxia_sect.yaml` |
| 科幻机甲文 | `sci_fi_mecha.yaml` |
| 无限流 | `infinite_flow.yaml` |
| 宫斗权谋文 | `palace_intrigue.yaml` |
| 言情总裁文 | `romance_ceo.yaml` |
| 悬疑犯罪文 | `suspense_crime.yaml` |
| 历史种田文 | `historical_farming.yaml` |
| 校园青春文 | `school_youth.yaml` |
| 短剧复仇文 | `short_drama_revenge.yaml` |

## 支持的字数规模

| 规模 | 配置文件 |
|------|---------|
| 3万字短篇 | `30k_short_novel.yaml` |
| 10万字中篇 | `100k_medium_novel.yaml` |
| 30万字网文 | `300k_web_novel.yaml` |
| 100万字长篇 | `1m_long_serial.yaml` |
| 200万字超长篇 | `2m_epic_serial.yaml` |

## 14个Agent说明

| Agent | 职责 |
|-------|------|
| Showrunner | 总编剧，把控全局方向 |
| Genre Strategist | 类型范本匹配与节奏校准 |
| Plot Architect | 总纲/分卷纲/章纲生成 |
| Character Keeper | 人设维护与弧线追踪 |
| Worldbuilding Keeper | 世界观与正典维护 |
| Power System Designer | 力量体系设计与平衡 |
| Chapter Writer | 章节正文生成 |
| Dialogue Agent | 对白优化与角色声音区分 |
| Pacing Doctor | 节奏诊断与水章检测 |
| Promise-Payoff Validator | 读者期待追踪与回收校验 |
| Continuity Checker | 时间线/道具/关系连续性检查 |
| Style Keeper | 文风统一性维护 |
| Commercial Hook Agent | 书名/简介/标签商业化 |
| Red Team Reviewer | 毒舌读者视角，找弃书点 |

## 核心原则

```
类型优先。
人物为魂。
章章有冲突。
定期给回报。
设定不能崩。
每场戏都要有用。
```
