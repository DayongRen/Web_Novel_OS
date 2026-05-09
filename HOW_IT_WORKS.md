# Web Novel OS — 执行演示

> 用《北地无夫》为例，完整走一遍 v2 流程，记录每条命令和实际产出。

---

## 测试环境

```
OS   : Linux 6.2 (Ubuntu)
Python : 3.10+
模型   : claude-opus-4-5 (Anthropic)
项目   : 北地无夫 · 300,000 字 · 晋江女频 · 仙侠
```

---

## Step 0：安装和配置

```bash
git clone https://github.com/YOUR_USERNAME/Web_Novel_OS.git
cd Web_Novel_OS

pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填入：
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
```

---

## Step 1：填写核心创意

编辑 `project_repo/outlines/00_core_idea.md`：

```markdown
北地苦寒，十年外敌入侵，男丁死伤殆尽，留下大量寡妇与未嫁女。
朝廷推行"珠婚制"——将俘获的异族男性、罪奴制成"珠男"，装入盲盒供女性购买。

女主沈照晚，北地粮商遗孀，为保住家业需要一个名义夫君，
花三百两买了一只"残品盲盒"，开出的却是外表病弱实则是异族质子的江澜。

两人假夫妻，真羁绊，最终以一纸停战协议终结北地十年战火。

类型定位：古代仙侠 · 先婚后爱 · 女频情感 · 战争背景
目标字数：30万字
平台：晋江文学城
```

---

## Step 2：配置 `novel_config.yaml`

```yaml
project:
  title: "北地无夫"
  target_word_count: 300000
  target_platform: "jjwxc_female"
  words_per_chapter: 2200

genre:
  primary: "xianxia_sect"
  secondary: ["romance_subline", "historical_farming"]
```

---

## Step 3：v2 完整流程执行

### 3.1 初始化

```bash
python runner.py init
```

**实际产出：**
```
runs/INIT/20260510_xxx/
├── User_Idea_Parsed.md      ← 创意解析报告
├── Genre_Match_Report.md    ← 类型匹配分析
├── Project_Audit.md         ← 总编剧审计
└── RedTeam_Concept_Review.md← 毒舌读者预审
```

---

### 3.2 项目画像生成（v2 新增）

```bash
python runner.py profile
```

**实际产出** `project_repo/manifests/Project_Profile.yaml`：

```yaml
project:
  title: 北地无夫
  target_word_count: 300000
  target_platform: jjwxc_female

genre:
  primary: xianxia_sect
  tone: 先婚后爱，轻喜剧开局，沉重战争收尾
  heat_level: medium
  complexity: medium

length_class:
  name: volume_200k          # ← 自动识别为 20-30 万字级别
  recommended_stage_model: five_act_or_volume

reader_contract:
  main_hook: "珠男身份悬念 + 假夫妻真情感"
  core_expectation: "感情推进 + 身份揭露 + 战争终结"
  emotional_payoff: "二人相守时的情感爆发"

production:
  chapter_card_policy: full_preplan  # ← 30万字以内全部预规划
  batch_size: 5
  review_interval_chapters: 20

inferred_needs:
  world_bible: true
  romance_arc: true          # ← 自动识别需要感情线账本
  faction_ledger: true       # ← 自动识别需要势力账本
  power_system: true
```

---

### 3.3 生产策略生成（v2 新增）

```bash
python runner.py strategy
```

**实际产出** `project_repo/manifests/Production_Strategy.yaml`：

```yaml
strategy:
  length_profile: volume_200k
  genre_profile: xianxia_sect
  platform_profile: jjwxc_female
  target_chapters: 136
  words_per_chapter: 2205

batch_policy:
  write_batch_size: 5
  quality_check_every: 5
  structural_review_every: 20
  major_reoutline_every: 50

chapter_card_policy:
  mode: full_preplan         # 全预规划

required_ledgers:
  - Character_Bible
  - Promise_Ledger
  - Power_System_Ledger
  - Faction_Ledger
  - Arc_Tracker
  - Relationship_Arc_Ledger  # ← 因 romance_arc=true 自动添加

quality_policy:
  active_gates:
    - universal
    - length_specific
    - genre_specific
  hard_fail:
    - missing_chapter_card
    - empty_chapter
    - canon_contradiction
```

**同时自动初始化账本：**
```
project_repo/canon/
├── Character_Bible.md        ← 新建（模板）
├── Faction_Ledger.yaml       ← 新建（空表）
├── Power_System_Ledger.yaml  ← 新建（空表）
├── Relationship_Arc_Ledger.yaml ← 新建（空表）
└── Ledger_Registry.yaml      ← 账本注册表
project_repo/continuity/
├── Promise_Payoff_Map.yaml   ← 新建
└── Character_Arc_Tracker.yaml← 新建
```

---

### 3.4 故事圣经生成

```bash
python runner.py run --stage bible
```

**实际产出（节选）：**

```markdown
# 人物圣经

## 沈照晚
- 身份：北地粮商遗孀，27岁
- 核心动机：保住家业，让弟妹安稳
- 性格：精明务实，习惯用交易理解关系
- 弱点：不擅长处理"不能用钱解决的问题"
- 弧线：求子保家 → 护家见众生 → 以停战为礼

## 江澜
- 身份：表面：残品珠男；实际：北疆质子
- 核心动机：活着回去，但逐渐舍不得离开
- 性格：外表顺从，内心清醒
- 弱点：不会主动表达情感，只会行动
```

---

### 3.5 总纲与章节卡片生成

```bash
python runner.py run --stage outline   # 生成 30 章细纲
python runner.py cards                 # full_preplan 模式：生成全部 136 章卡片
```

**章节卡片示例（第1章）：**

```yaml
- chapter: 1
  title: "开盒"
  word_target: 2200
  chapter_function:
    - "建立北地无夫的世界背景"
    - "展示女主沈照晚的务实性格"
    - "第一次开盒——惊喜与麻烦并存"
  scene_list:
    - scene_id: S1.1
      location: 北地集市盲盒摊
      goal: 沈照晚挑选盲盒
      conflict: 预算有限，好盒被抢
      turn: 老板推荐"残品特价盒"
    - scene_id: S1.2
      location: 沈家宅院
      goal: 开盒
      conflict: 开出的不是壮劳力，是个病弱男人
      turn: 男人睁眼，眼神锐利得不像残品
  reader_payoff:
    - "北地世界观建立"
    - "男主第一次亮相的悬念"
  ending_hook: "他开口说的第一句话，用的是北疆口音。"
  promise_opens:
    - "江澜的真实身份"
```

---

### 3.6 通用生产（v2 核心命令）

```bash
# 写第 1-5 章
python runner.py produce

# 持续循环直到完成
python runner.py produce --loop
```

**每批次完成后自动运行：**

```
第1-5章写完
  ↓ 自适应质量门检查
    ✅ 通用层：字数/连续性/钩子
    ✅ 长度层：midpoint_turn（第20章后激活）
    ✅ 题材层：emotional_progression（言情感情推进检测）
  ↓ Promise-Payoff Patch（只追加，不覆盖）
  ↓ Canon Delta 提取（新人物/地点自动写入账本）
  ↓ 快照（每10章）
```

**第20章结构复盘自动触发：**
```
Structural_Review_Ch0020.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━
主线进展：假夫妻关系建立完成，感情线刚刚开始
读者期待满足度：悬念维持良好，珠男身份未泄露
建议：第21-30章需要推进粮道危机，增加外部压力
```

---

### 3.7 校验

```bash
python runner.py check
```

**示例输出：**
```
✅ 字数预算     平均 2210字/章（目标 2200，偏差 0%）
✅ 节奏检查     近20章无水章
⚠️ 承诺-回报    P003「江澜身份揭露」预计第40章，当前第35章，即将逾期
✅ 类型承诺     感情线推进承诺已登记
✅ 连续性       时间线无矛盾
✅ 人物一致性   沈照晚弧线正常推进
✅ 账本状态     6个账本均在维护中
```

---

### 3.8 导出

```bash
python runner.py export
```

**产出（volume_200k 级别自动决定）：**
```
project_repo/manuscript/final_export/
├── final.md              ← 完整正文
├── final.txt             ← 纯文本版
├── final.docx            ← Word 文档
├── chapter_index.md      ← 章节索引（136章）
└── continuity_report.md  ← 连续性最终报告
```

---

## Studio 模式（可视化工作台）

```bash
python start_studio.py
# 浏览器打开 http://localhost:8765
```

**Studio 实现同等流程的对话方式：**

1. 首页点「我有一个小说想法」
2. 输入：*北地女人买盲盒夫君，开出异族质子，带来停战*
3. 系统引导 6 轮问答（故事重心 / 主角身份 / 开局风格 / 节奏 / 世界观深度）
4. 系统生成 3 个故事方案供选择
5. 选择后自动触发 bible → outline → 章卡生成
6. 写作页按章选择，点「生成本章」，结果进 session 沙盒
7. 满意则点「采纳」写入正式项目

---

## 费用参考（Anthropic claude-opus-4-5）

```bash
python runner.py cost
```

| 阶段 | 调用次数 | 约费用(USD) |
|------|---------|-----------|
| profile + strategy | 2 | ~$0.03 |
| bible | 6 | ~$0.15 |
| outline + cards | 8 | ~$0.20 |
| produce 136章 | ~160 | ~$4.00 |
| revision | 5 | ~$0.10 |
| **合计** | **~181** | **~$4.50** |

> 使用 claude-sonnet-4-5 可降低约 80% 费用（约 $0.90）。
> 在 `novel_config.yaml` 中修改 `model.name` 即可切换。
