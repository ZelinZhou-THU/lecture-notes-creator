---
name: lecture-notes-creator
description: 将晦涩的课件（PDF）转化为易懂的本科生自学讲义（Markdown），含子智能体review迭代和Notion上传。使用MinerU API高质量提取PDF内容（默认vlm模式，公式表格完美保留），分析课件每页内容，按课件页码标注对照关系，子智能体review后迭代优化，最终上传到Notion。支持两种课件类型：(1) 传统分节式课件（物理、化学、材料科学等），以直觉类比→数学推导→物理意义的认知路径讲解；(2) 幻灯片式课件（CS、AI等），以问题/动机→核心机制→应用/意义的认知路径讲解，LLM自动聚类主题。讲义始终用中文撰写，关键术语附英文原词。触发词："讲义"、"课件讲解"、"考点总结"、"课程笔记"、"lecture notes"、"从课件生成讲义"、"分析课件"、"上传讲义到Notion"。
---

# Lecture Notes Creator

将晦涩的学术课件转化为易懂的本科生自学讲义，含review迭代和Notion上传。

## 工作流程

### 0. 准备与切分（长PDF需要）

当课件 PDF 超过 MinerU 页数限制（200页）或超过 LLM 可处理的上下文长度时，需要先切分。

#### 0a. 分析 PDF 基本信息

```bash
python scripts/split_pdf.py analyze "path/to/courseware.pdf" --preview 3
```

输出：总页数、文件大小、是否需要预切分、TOC 检测结果（自动识别章节标题）、前几页文本预览。

**判断逻辑：**
- ≤200 页 → 直接进入 Step 1（MinerU 提取）
- >200 页 → 执行 0b（预切分），再对每个子 PDF 分别 MinerU 提取后合并

#### 0b. 预切分大 PDF（>200页时）

```bash
python scripts/split_pdf.py pre_split "input.pdf" --output ./pre_split --chunk-size 150
```

按页数切分为多个子 PDF（每个 ≤150 页），然后对每个子 PDF 分别调用 Step 1 的 MinerU 提取，最后合并：

```bash
python scripts/split_pdf.py merge_md ./chunk1_mineru/full.md ./chunk2_mineru/full.md --output ./mineru/full.md
```

合并时会自动处理图片路径（复制到统一的 `images/` 目录）。

#### 0c. 课件类型检测

MinerU 提取得到完整 `full_with_pages.md` 后，**先判断课件类型**，再决定后续处理路径。

**LLM 分析 `full_with_pages.md` 结构**，检测以下信号：

| 检测信号 | 传统分节式（traditional） | 幻灯片式（slide-based） |
|----------|--------------------------|------------------------|
| 每页平均文本量 | 高（密集段落、连续叙述） | 低（标题+要点、短句） |
| 章节编号 | 有明确的 `## X.Y` 编号标题 | 无正式编号，页面标题独立 |
| 页面间连贯性 | 强（同一段落的延续） | 弱（每页自含主题） |
| 典型课程 | 物理、化学、材料科学 | CS、AI、工程类 |

输出：
```json
{
  "courseware_type": "traditional" | "slide-based"
}
```

根据类型进入不同的后续处理：

---

#### 0d-traditional. 按章节切分 Markdown（仅 traditional 类型）

**前置条件：`courseware_type == "traditional"`**

如果章节很长，可以物理切分为独立的章节文件：

1. **识别章节标题**（如 `## 4.1 自由电子Fermi气`），确定切分点
2. **生成切分计划**（JSON）并执行：

```bash
python scripts/split_pdf.py split_md ./mineru/full_with_pages.md --plan split_plan.json --output ./sections
```

切分计划格式（由 LLM 生成）示例：
```json
{
  "sections": [
    {"heading": "# 4.1", "start_marker": null, "title": "4.0_序言+4.1"},
    {"heading": "# 4.2", "start_marker": "# 4.2", "title": "4.2_Bloch定理"},
    {"heading": "# 4.3", "start_marker": "# 4.3", "title": "4.3_近自由电子近似"}
  ]
}
```

**`start_marker` 字段规则：**
- **首节**：`start_marker: null` 或 `start_marker: ""` → 从文件开头（第 0 行）开始，包含前言/目录等所有内容
- **后续节**：`start_marker` 必须为具体字符串（如 `"# 4.2"` 或 `"4.2 Bloch定理"`），用于定位该章节的 Markdown 标题行。空值会导致该节被跳过。
- **匹配逻辑**：`_find_heading_line()` 只匹配以 `#` 开头的 Markdown 标题行，避免表格正文中的数字（如 `4.73`）产生误匹配。

**混合策略**：短章节（<30页）直接从 `full.md` 中读取对应段落即可，无需物理切分。只有长章节（>30页）才需要物理切分为独立文件。

---

#### 0d-slide. 主题聚类（仅 slide-based 类型）

**前置条件：`courseware_type == "slide-based"`**

幻灯片式课件没有明确的章节编号，每页是一张独立幻灯片。需要 **LLM 自动识别主题边界**，将连续相关的幻灯片聚类为 Topic。

**LLM 读取 `full_with_pages.md`**，执行主题聚类：
1. 逐页扫描内容，识别主题切换点（标题含义变化、新概念引入、从理论转到应用等）
2. 将连续相关页面归为一个 Topic
3. 每个 Topic 需要有清晰的中文标题和对应的页码范围

输出 **Topic Map**（JSON）：
```json
{
  "courseware_type": "slide-based",
  "topics": [
    {"title": "Self-Attention 机制", "page_range": [5, 25]},
    {"title": "Multi-Head Attention", "page_range": [26, 40]},
    {"title": "位置编码（Positional Encoding）", "page_range": [41, 55]},
    {"title": "完整 Transformer 架构", "page_range": [56, 74]}
  ]
}
```

**聚类原则：**
- 每个 Topic 对应一个完整的知识点或子主题
- Topic 内的页面必须是连续的（不允许跳跃合并）
- Topic 之间允许存在过渡页/回顾页，这些页面归入前一个或后一个 Topic（由 LLM 判断语义归属）
- 单个 Topic 不宜超过 30 页；如果超过，考虑拆分为更细粒度的子主题
- 标题使用中文，关键术语附英文原词

### 1. 提取课件内容

#### 1a. MinerU 高质量文字提取（首选，用户手动运行模式）

**重要：为避免 OpenCode 内存泄漏导致系统崩溃，MinerU 提取必须在 OpenCode 外部运行。**

**工作流程：**

1. **OpenCode 生成 .bat 文件**（一次性）：
   ```bash
   python scripts/create_extraction_bat.py "path/to/courseware.pdf" --output ./output_dir/mineru --mode auto
   ```

2. **用户双击运行 .bat 文件**（在文件管理器中）：
   - 打开输出目录 `./output_dir/mineru/`
   - 双击 `run_extraction.bat`
   - 等待提取完成（CMD 窗口会显示进度）

3. **用户告诉 OpenCode 提取完成**：
   - 在 OpenCode 中输入 "提取完成" 或 "extraction done"
   - OpenCode 检查 `extraction_status.json` 确认状态

4. **OpenCode 继续后续步骤**：
   - 读取 `full_with_pages.md` 分析结构
   - 编写讲义
   - Review 和 Notion 上传

**产出文件：**
- `output_dir/mineru/full.md`（原始 Markdown，公式 LaTeX、表格 HTML，**无页码**）
- `output_dir/mineru/full_with_pages.md`（重建版本，每段内容前标注 `> [课件 P{N}]`，**需经 Step 1c 图片理解后处理才用于写讲义**）
- `output_dir/mineru/images/`（提取的嵌入图片，供 Step 1c 图片理解使用）
- `output_dir/mineru/extraction_status.json`（提取状态文件，用于跟踪进度）
- `output_dir/mineru/run_extraction.bat`（可双击运行的批处理文件）

**Token 配置**：在项目根目录 `.env` 文件中设置 `MINERU_TOKEN=your_key`（从 https://mineru.net/ 获取），脚本会自动加载，无需每次手动设置环境变量。

**模式说明：**
- `--mode vlm`（默认，推荐）：高精度模式，适合公式密集/复杂表格/图文混排的课件
- `--mode pipeline`：快速模式，适合纯文字/简单排版的文档
- `--mode auto`：等同于 vlm（自动分类已禁用，直接使用 vlm 模式）

**注意事项：**
- .bat 文件会自动打开输出目录，方便用户查看结果
- 如果提取失败，CMD 窗口会显示错误信息并暂停
- 用户只需双击 .bat 文件，无需手动输入命令
- 提取完成后，用户告诉 OpenCode "提取完成"，OpenCode 会检查状态文件并继续

#### 1b. 生成页面截图（MinerU 失败时回退）

```bash
python scripts/extract_pdf.py "path/to/courseware.pdf" --output ./output_dir --text-only --dpi 200
```

产出：`output_dir/images/page_NN.png`（每页截图）+ `output_dir/summary.txt`（页面统计）。

**何时生成页面截图：**
- MinerU **成功**：页面截图**不需要**单独生成（MinerU 输出已包含高质量文字和图片）
- MinerU **失败**：自动回退到 `extract_pdf.py`，此时生成页面截图 + 逐页文字作为替代

如果需要逐页浏览课件原始画面作为辅助参考（即使 MinerU 成功），也可以手动运行此步骤。

#### 1c. 图片理解后处理（可选）

> ⚠️ 当课件中存在较多图片（如架构图、流程图、实验结果图）时，建议执行此步骤。MinerU 提取的图片已自动重命名为 `img_001.jpg` ~ `img_NNN.jpg`（按 md 中出现顺序），但图片内部结构无法被理解。此步骤通过多模态模型对每张图片生成文字描述并回填到 Markdown。

**流程：子智能体分析图片 → 分批增量保存JSON → 合并回填**

使用 Task 工具派出 `image-describer` 子智能体，它会自动完成全流程：

```
输入：
- 图片目录：output/mineru/images/（文件名已按出现顺序编号）
- 原始 Markdown：output/mineru/full_with_pages.md
- 输出 Markdown：output/mineru/full_with_pages_described.md

子智能体执行流程：
1. 列出 images/ 目录，按文件名排序即为 md 中出现顺序
2. 分批处理（每批≤5张），每批内串行调用 zai-mcp-server_analyze_image
3. 每批完成后立即用 save_batch_json.py 保存 JSON（增量保存）
4. 全部完成后调用 backfill_image_descriptions.py 合并回填
```

> ⚠️ **批次间串行约束（硬性规则）**：禁止同时 dispatch 多个 image-describer 子智能体处理不同 batch。一个 batch 完成并保存 JSON 后，才开始下一个 batch。违反此约束将导致 rate limit 错误。

回填格式：
```markdown
> **图片内容：**
> 图片描述文字（400字以内）
> ![](images/img_NNN.jpg)
```

**子智能体配置：**
- 配置文件：`.opencode/agents/image-describer.md`（完整提示词模板和执行流程）
- 工具：`zai-mcp-server_analyze_image` + `bash`（调用 save_batch_json.py 和回填脚本）
- 执行流程：详见 `.opencode/agents/image-describer.md`

**新增脚本：**
- `scripts/save_batch_json.py`：增量保存图片描述到 JSON（避免 PowerShell 编码问题）

**修改脚本：**
- `scripts/backfill_image_descriptions.py`：支持多 batch JSON 文件合并（逗号分隔）

**后续步骤说明：**
- Step 2（分析课件结构）使用 `full_with_pages_described.md` 而非原始 `full_with_pages.md`
- 其余步骤不变

### 2. 分析课件结构

读取 MinerU 输出的 `full_with_pages_described.md`（图片描述已回填）或原始 `full_with_pages.md`，建立内容地图。

如果 MinerU 不可用（已回退到 extract_pdf.py），则逐页读取 `text/page_NN.txt` + 页面截图。

#### Traditional 类型

- 记录每页的核心概念、公式、图表
- 识别逻辑链条：概念引入→推导→结论→应用
- 标注页面之间的依赖关系（哪些页面是同一主题的延续）
- 标记习题页和实验方法页

#### Slide-Based 类型

基于 Step 0d-slide 生成的 Topic Map，为每个 Topic 建立详细的内容地图：
- 记录 Topic 内每页的核心内容（公式、算法、概念、图表）
- 识别每个 Topic 内的逻辑链条：问题/动机→核心机制→应用/意义
- 标注跨 Topic 的依赖关系（如 Topic B 引用了 Topic A 的概念）
- 标记每个 Topic 的核心幻灯片和辅助性幻灯片（如 recap、示例图）

### 3. 编写讲义（页码驱动，严格按课件页码顺序）

**核心原则：讲义的内容组织严格按照原课件的页码顺序（P1→P2→P3→...）。** 标题中直接嵌入页码范围，方便学生逐页对照自学。

**讲义始终用中文撰写，关键术语首次出现时用括号补充英文原词**（如"自注意力机制（Self-Attention）"）。

根据 `courseware_type` 使用不同的模板：

---

#### Traditional 模式模板

**适用：** 物理、化学、材料科学等传统分节式课件。

**认知路径：直觉类比 → 数学推导 → 物理意义**

每章一个独立 Markdown 文件：

```markdown
# 第X节 标题

## 一、本节概述
（2-3句话：讨论什么问题、为什么重要、与前节的联系。标注本节覆盖的课件页码范围）

## 二、核心概念与推导（按课件页码顺序）

### 2.1 [课件P1] 能态密度（DOS）的定义
（先给直觉类比，再给数学推导，最后总结物理意义）

> **类比理解：** ...
> **物理直觉：** ...

**数学推导：**
（step by step，每步有解释）

**结论：** ...

### 2.2 [课件P2] 自由电子模型：3D/2D/1D的DOS解析解
...

### 2.3 [课件P3-P4] 近自由电子DOS与带隙效应
...

### 2.4 [课件P5] 例题：简单立方晶格s态能带的DOS
...

### 2.5 [课件P8] Van Hove奇异性
...

## 三、实验方法（如有，仍按课件页码顺序）

### 3.X [课件P15] X射线发射谱（XES）
（原理→装置→数据→能得出什么信息）

### 3.X+1 [课件P17-P18] UPS与ARPES
...

## 四、常见误区与辨析
（易混淆概念对比表。此节不对应特定课件页面，是对全文的总结性辨析）

## 五、考点总结
### 概念题 | 计算题 | 证明题 | 分析题

## 六、课件页码自查清单

以下表格覆盖本节**所有**课件页面。每学完一页，在✅列打勾确认。

| ✅ | 课件页码 | 讲义对应章节 | 核心内容 |
|---|---------|------------|---------|
| [ ] | P1 | 2.1 [P1] DOS定义 | DOS定义与k空间推导 |
| [ ] | P2 | 2.2 [P2] 自由电子DOS | 3D/2D/1D解析解 |
| [ ] | P3-P4 | 2.3 [P3-P4] 近自由电子DOS | 带隙效应对比图 |
| [ ] | ... | ... | ... |

**注意：** 如果对照表中有任何课件页码缺失，说明该页内容未在讲义中讲解。
```

---

#### Slide-Based 模式模板

**适用：** CS、AI、工程类等幻灯片式课件。

**认知路径：问题/动机 → 核心机制/算法 → 应用/意义**

每个 Lecture 一个独立 Markdown 文件。基于 Step 0d-slide 的 Topic Map 组织结构——每个 Topic 对应一个 `##` 级别的章节，Topic 内按页码递增展开：

```markdown
# Lecture 04: Self-Attention and Transformer Architecture 讲义

## 一、本讲概述
（2-3句话：本讲覆盖的核心主题、与前讲的联系、整体学习目标。标注页码范围 P1-P74）

## 二、Self-Attention 机制 （课件P5-P25）

本节介绍自注意力机制（Self-Attention）的动机、核心计算和直觉理解。

### [课件P5] 为什么需要 Self-Attention

> **问题背景：** RNN 的顺序计算瓶颈和长距离依赖问题使得......

### [课件P6-P8] 注意力分数的计算

**核心思想：** ...

> **直觉理解：** 可以把注意力想象成"图书馆找书"——......

**数学表达：**
$$e_{ij} = \text{score}(h_i, h_j)$$

### [课件P9-P12] Scaled Dot-Product Attention

**核心公式：**
$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

> **直觉理解：** 除以 $\sqrt{d_k}$ 的目的是......

**关键要点：** ...

...

## 三、Multi-Head Attention （课件P26-P40）

本节介绍多头注意力机制（Multi-Head Attention），它如何让模型从不同表示子空间中捕获信息。

### [课件P26] 从单头到多头：动机

...

### [课件P27-P30] Multi-Head Attention 的计算

$$\text{MultiHead}(Q, K, V) = \text{Concat}(\text{head}_1, ..., \text{head}_h)W^O$$
$$\text{head}_i = \text{Attention}(QW_i^Q, KW_i^K, VW_i^V)$$

...

## 四、位置编码 （课件P41-P55）
...

## 五、完整 Transformer 架构 （课件P56-P74）
...

## 六、常见误区与辨析
（易混淆概念对比表。此节不对应特定课件页面）

| 概念 | 区别 | 适用场景 |
|------|------|---------|
| Self-Attention vs Cross-Attention | ... | ... |
| ... | ... | ... |

## 七、考点总结

### 概念题 | 推导题 | 分析题 | 设计题

## 八、课件页码自查清单

以下表格覆盖本讲**所有**课件页面。每学完一页，在✅列打勾确认。

| ✅ | 课件页码 | 讲义对应章节 | 核心内容 |
|---|---------|------------|---------|
| [ ] | P1 | 一、本讲概述 | 标题页 |
| [ ] | P2-P4 | 一、本讲概述 | 回顾 |
| [ ] | P5 | 二、Self-Attention | 为什么需要Self-Attention |
| [ ] | P6-P8 | 二、Self-Attention | 注意力分数计算 |
| [ ] | ... | ... | ... |

**注意：** 如果对照表中有任何课件页码缺失，说明该页内容未在讲义中讲解。
```

---

#### 页码标注规则（两种模式通用）

1. **标题格式**：`### N.M [课件PX] 标题`（traditional）或 `### [课件PX] 标题`（slide-based，页码紧跟 ### 在标题最前面）
2. **严格递增**：所有小节页码**单调递增**，不允许回跳
3. **连续页面合并**：连续多页属于同一主题时合并为 `[课件P3-P4]` 一个小节，但传统模式不超过3页合并；slide-based 模式可适当放宽（因幻灯片信息密度较低）
4. **交叉引用例外**：当讲解某页内容时需要引用后续页面的概念，用 `> **注：关于XXX的详细讨论见 [课件P15]（第X节）**` 标注，但**不在当前位置展开**
5. **每一页必须覆盖**：对照表中不能有任何课件页码缺失。纯图片页面也要标注
6. **习题页处理**：习题页在讲义中标注为独立小节，给出参考答案框架
7. **Slide-based 特有**：Topic（`##` 级别）对应一个连续页码范围，Topic 内的页面连续，Topic 之间的页码范围可以不连续（中间的过渡/回顾页归入语义最接近的 Topic）

### 4. 编写考点汇总

所有章节完成后，输出一个跨章节的考点汇总文件，包含：
- **核心公式速查表**（公式 + 含义 + 重要程度★★★）
- **概念题**（名词解释/简答的标准答案框架）
- **计算题**（典型计算步骤和数值示例）
- **证明题**（推导思路和关键步骤）
- **综合分析题**（跨章节综合）
- **考前自查清单**（checkbox格式）

### 5. 子智能体Review迭代（每章完成后）

> ⚠️ **重要：这是一个循环迭代过程，不是单次Review！修改后必须再次Review，直到满足终止条件才能进入Step 6。**

**每章讲义写完后**，使用 `lecture-reviewer` 子智能体以本科生自学视角review（配置在 `.opencode/agents/lecture-reviewer.md`）。该子智能体使用免费模型，temperature=0.3，仅有只读权限（edit: deny, bash: deny）。

**Review循环（必须完整执行，不可跳过）：**

```
round = 0
while True:
    round += 1
    ┌─ 子智能体Review（用Task工具派出 lecture-reviewer 子智能体）
    │  输入：讲义路径 + 原课件 md 路径（full_with_pages.md）
    │  输出：7维度评分 + Critical/Major/Minor建议
    │
    ├─ 终止条件检查：
    │  ✅ 总评分 ≥ 8/10 且无Critical建议 → 跳出循环
    │  ✅ round == 3 → 跳出循环
    │  ✅ 连续2轮无新见解 → 跳出循环
    │  ❌ 以上都不满足 → 继续
    │
    ├─ 主智能体评估每条建议（逐条决定采纳/拒绝+理由）
    │
    └─ 主智能体修改讲义（采纳的建议立即修改）
    → 回到循环开头，用修改后的讲义再次Review
```

**子智能体评估的7个维度：**

| 维度 | 权重 | 评估标准 |
|------|------|---------|
| 概念清晰度 | 20% | 每个新概念是否有清晰定义和类比；术语首次出现是否有解释 |
| 推导连贯性 | 15% | 数学推导每步是否可追溯；是否有未解释的跳步 |
| 逻辑衔接 | 10% | 段落/章节之间是否有自然的过渡；是否存在逻辑断层 |
| 类比恰当性 | 10% | 类比是否贴近生活经验；是否引入了比原概念更难的新概念 |
| 页码顺序严格性 | 10% | 小节标题页码是否严格递增；对照表是否覆盖所有页面 |
| 自学对照友好度 | 10% | 学生能否拿着原课件逐页对照学习；页码标注是否一目了然 |
| 内容准确性 | 25% | 讲义是否准确反映原课件内容；是否有错误解读、遗漏重要内容 |

### 6. 上传到Notion

> ⚠️ **前置条件：所有章节的Review迭代必须全部终止后，才能执行此步骤。禁止在Review循环未结束时上传Notion。**

**前置条件：** 需要已安装 `notion` skill，且API key已配置。

#### 6.1 表格问题预检查

上传前**必须**运行预检查脚本，检测三类问题：

```bash
python deps/notion/scripts/check_markdown_for_notion.py <markdown_file>
```

**检测项：**
1. **LaTeX pipe `|` 未转义** — 含有 `|` 的公式（如 `$\hat{p}(y|x)$`）会打乱表格列解析
2. **行间 cell 数量不一致** — header 和 body 的列数不匹配
3. **表格行数 > 100** — Notion API 上限单个 table block 的 children 为 100 行

如果有问题，脚本会提示具体位置和行号。**必须修复后才能上传。**

#### 6.2 表格修复原则

**1. LaTeX pipe 单元格 → 改列表格式**
含有 LaTeX `|` 的单元格不要用 markdown 表格，改用列表格式：

```markdown
原（有问题）：
| 方法 | 公式 |
|------|------|
| Imitation | 学习 $\hat{p}(y|x)$ |

改（无问题）：
**Imitation 方法**：学习 $p(y|x)$，描述...
```

**2. 对照表超过 100 行 → 在合适位置插入 `---` 强制拆分**
Notion 上传时连续 markdown 表格会作为一个 table block 整体上传，如果超过 100 行会报错。修复方法是在第 50 行左右（或自然语义断点）插入 `---` 水平线：

```markdown
| ✅ | 课件页码 | 讲义对应章节 | 核心内容 |
|---|---------|------------|---------|
| [ ] | P1 | ... | ... |
| [ ] | P50 | ... | ... |

---

| ✅ | 课件页码 | 讲义对应章节 | 核心内容 |
|---|---------|------------|---------|
| [ ] | P51 | ... | ... |
```

这样 markdown 解析为两个独立的 table block，每个都不超过 100 行。

#### 6.3 上传流程
1. **查找"课程学习"页面**：用Notion API搜索 "课程学习"，确认其 page_id
2. **查找或创建课程页面**：在"课程学习"下查找是否已有对应课程（如"固体物理"）的子页面，不存在则创建
3. **查找或创建章节页面**：在课程页面下查找或创建章节子页面（如"第四章"）
4. **上传讲义**：用 `notion` skill 的 `add_markdown_to_page.py` 将每个讲义文件上传为子页面
5. **上传考点汇总**：作为独立子页面上传到章节页面下

**Notion页面层级：**
```
课程学习（已有）
└── 固体物理（查找/创建）
    └── 第四章（查找/创建）
        ├── 讲义_4.9_能态密度与费米面（上传）
        ├── 讲义_4.10_低维系统中的电子态（上传）
        ├── 讲义_4.11_无序系统中的电子态（上传）
        └── 讲义_第四章_考点汇总（上传）
```

**上传脚本调用：**
```bash
# 创建子页面
python deps/notion/scripts/archive_and_create_pages.py <parent_page_id> --titles "讲义_4.9_能态密度与费米面"

# 上传内容
python deps/notion/scripts/add_markdown_to_page.py <new_page_id> "讲义_4.9_能态密度与费米面.md"
```

## 写作原则

1. **先直觉后数学**：每个公式前先用日常类比建立物理图像（traditional 模式）或先说明动机再给机制（slide-based 模式）
2. **推导步步可追溯**：每步变换标注用了什么原理/近似
3. **公式用LaTeX**：行内 `$...$`，独立行 `$$...$$`
4. **关键术语中英对照**：首次出现时标注英文（如"多头注意力（Multi-Head Attention）"）
5. **辨析用表格**：易混淆概念并排对比
6. **考点按题型分类**：概念题/计算题/证明题/分析题
7. **不要主动停下**：从开始到所有章节+考点汇总+review+Notion上传全部完成，中间不暂停
8. **保持逻辑连贯**：按章节顺序执行，后续章节可引用前面的概念
9. **页码驱动结构**：讲义内容严格按课件P1→P2→P3顺序组织
10. **每页必现**：对照表必须覆盖所有课件页面，缺一页即为Critical缺陷
11. **Review建议具体可操作**：子智能体反馈必须定位到具体段落，不能泛泛而谈
12. **语言**：讲义始终用中文撰写，无论课件原文是中文还是英文
13. **认知路径适配**：传统理科课件用"直觉类比→数学推导→物理意义"；CS/AI 类幻灯片课件用"问题/动机→核心机制→应用/意义"
14. **主题聚类**：幻灯片课件由 LLM 自动识别主题边界并聚类，不以单页为最小组织单位
15. **讲义越详细越好**：即使课件已提供推导和结论，若逻辑关系无法从上下文显然得到，必须详细解读。详见 `references/writing-style-guide.md`

## 输出文件

```
<output_dir>/
├── pre_split/                  ← 预切分的子PDF（>200页时才有）
│   ├── chunk_001.pdf
│   ├── chunk_002.pdf
│   └── manifest.json
├── sections/                   ← 物理切分的章节MD（长章节）
│   ├── section_4.1_标题.md
│   ├── manifest.json
│   └── images/
├── 讲义_X.X_章节标题.md      ← 每章一个（含页码标注）
├── 讲义_X.X_章节标题.md
├── 讲义_第X章_考点汇总.md    ← 跨章汇总
└── mineru/                    ← MinerU 输出（成功时，核心）
    ├── full.md                ← 原始 Markdown（无页码）
    ├── full_with_pages.md     ← 带页码版本（MinerU 原始输出）
    ├── full_with_pages_described.md ← 图片理解版本（Step 1c 回填后，供写讲义用）
    ├── content_list.json      ← 结构化内容块（每页 blocks，含页码来源）
    ├── content_list_v2.json    ← 同上，v2 版本
    ├── images/                ← 提取的嵌入图片（已重命名为 img_001.jpg ~ img_NNN.jpg）
    └── layout.json            ← 版面分析

# MinerU 失败时（回退）：
<output_dir>/
├── images/
│   └── page_NN.png            ← 页面截图
├── summary.txt                ← 页面统计
└── text/
    └── page_NN.txt            ← 逐页文字
```

## 依赖

- **notion** skill（用于上传到Notion）：已内置在 `deps/notion/`，需配置API key
- **MinerU API**（高质量 PDF 提取）：在项目根目录 `.env` 文件中设置 `MINERU_TOKEN=your_key`（从 https://mineru.net/ 获取），脚本会自动加载
- **OCR工具**（用于图片页面文字提取）：`zai-mcp-server_extract_text_from_screenshot`
- **pdfplumber** + **pdf2image**（页面截图 + PDF 分析 + fallback 文字提取，已包含在 `scripts/extract_pdf.py`）
- **pypdf**（PDF 预切分，已包含在 `scripts/split_pdf.py`）
- **requests**（MinerU API 调用，已包含在 `scripts/mineru_extract.py`）

## MinerU API 注意事项

### API 调用流程（本地文件）

MinerU v4 API 的**本地文件上传**流程与 URL 提交不同：

```
1. POST /api/v4/file-urls/batch
   Body: {"files": [{"name": "file.pdf"}], "model_version": "vlm"}
   Response: {"data": {"batch_id": "xxx", "file_urls": ["presigned_url"]}}

2. PUT presigned_url  (上传文件，不设 Content-Type)
   → 系统自动提交解析任务，无需手动调用 submit

3. GET /api/v4/extract-results/batch/{batch_id}  (轮询结果)
   Response: {"data": {"extract_result": [{"state": "done", "full_zip_url": "..."}]}}
```

### API 踩坑记录

1. **请求体格式**：`/api/v4/file-urls/batch` 的 `files` 字段是对象数组 `[{"name": "xxx.pdf"}]`，不是字符串数组 `["xxx.pdf"]`。旧文档中的 `file_names` 参数已废弃。
2. **自动提交**：文件上传到 presigned URL 后，系统**自动提交解析任务**，不需要再调用 `/api/v4/extract/task`。手动提交会导致重复任务。
3. **批量结果字段**：轮询批量结果时，任务列表在 `data.extract_result`（不是 `data.task_results` 或 `data.results`）。
4. **上传无需 Content-Type**：PUT 上传文件时不要设置 Content-Type header，让 requests 自动处理。
5. **model_version vs layout_model**：`model_version` 控制解析引擎（`pipeline`/`vlm`/`MinerU-HTML`），`layout_model` 控制版面分析模型（`doclayout_yolo` 快速/`layoutlmv3` 精确）。当前脚本使用 `model_version`。

### 可用参数

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `model_version` | 解析引擎 | `pipeline`（快速）/ `vlm`（推荐，高精度）/ `MinerU-HTML` |
| `layout_model` | 版面分析模型 | `doclayout_yolo`（快速）/ `layoutlmv3`（精确） |
| `enable_formula` | 公式识别 | `true`/`false`（默认 true） |
| `enable_table` | 表格识别 | `true`/`false`（默认 true） |
| `language` | 语言 | `auto`/`ch`/`en` |

### 限制

- 单文件 ≤ 200MB，≤ 200 页
- 每天前 1000 页高优先级，超出后优先级降低
- presigned URL 有效期 24 小时

## Resources

### scripts/
- `split_pdf.py` — PDF 分析/预切分 + Markdown 合并/切分（长 PDF 处理）
- `extract_pdf.py` — 从PDF提取页面截图（+ fallback 文字提取）
- `mineru_extract.py` — MinerU API 高质量 PDF→Markdown 转换（默认 vlm 模式）
- `reconstruct_full_md.py` — 从 `content_list_v2.json` 重建带页码的 `full.md`（> [课件 P{N}] 标注）
- `backfill_image_descriptions.py` — 将图片描述 JSON 回填到 `full_with_pages.md`，生成 `full_with_pages_described.md`（支持多 JSON 文件逗号分隔合并）
- `save_batch_json.py` — 增量保存图片描述到 JSON 文件（避免 PowerShell 编码问题）

### references/
- `writing-style-guide.md` — 讲义写作风格指南和模板
- `review-prompt.md` — 子智能体review的提示词模板（备份，已嵌入 `.opencode/agents/lecture-reviewer.md`）