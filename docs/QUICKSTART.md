# Quick Start Guide 快速开始指南

## Workflow Overview 工作流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Lecture Notes Creator 工作流程                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │  0. PDF 分析   │    │ 1. MinerU   │    │  2. OpenCode 自动处理    │  │
│  │  (可选)       │ -> │   提取       │ -> │  (图片理解→分析→写讲义)   │  │
│  │  split_pdf   │    │ (用户双击)   │    │  + Review迭代            │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘  │
│                                                   │                      │
│                                                   v                      │
│                      ┌──────────────────────────────────────────────┐    │
│                      │         3. 上传到 Notion（可选）              │    │
│                      └──────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘

详细步骤 / Detailed Steps:

Step 0: PDF 分析 (PDF Analysis)
    └─ split_pdf.py analyze → 判断是否需要切分 / Determine if splitting needed

Step 1: MinerU 提取 (MinerU Extraction)
    └─ create_extraction_bat.py → 生成 .bat 文件 / Generate .bat file
    └─ 用户双击运行 / User double-clicks to run

Step 2-5: OpenCode 自动处理 (OpenCode Automatic Processing)
    ├─ 2. 图片理解 (image-describer sub-agent)
    ├─ 3. 分析课件结构 (analyze structure)
    ├─ 4. 编写讲义 (write lecture notes)
    └─ 5. Review 迭代 (review iterations)

Step 6: 上传 Notion (Upload to Notion)
    └─ check_markdown_for_notion.py → add_markdown_to_page.py
```

## Step 0: PDF 分析 (Optional 超过200页时才需要)

```bash
python scripts/split_pdf.py analyze "path/to/courseware.pdf" --preview 3
```

**判断逻辑 / Decision Logic:**
- ≤200 页 → 直接进入 Step 1
- >200 页 → 执行预切分，再分别提取后合并

## Step 1: MinerU 提取

### 1a. 生成 .bat 文件（推荐）

```bash
python scripts/create_extraction_bat.py "path/to/courseware.pdf" --output ./output_dir/mineru --mode auto
```

- `--mode vlm`（默认，推荐）：高精度模式，适合公式密集/复杂表格
- `--mode pipeline`：快速模式，适合纯文字/简单排版

> **为什么生成 .bat 文件而不是直接运行？**
> OpenCode 终端在检测到大量 IO 操作（如 MinerU 的批量文件下载/删除）后容易卡顿死机。
> 因此采用生成 .bat 文件 → 用户双击运行 → 完成后在 OpenCode 中继续的方案。

### 1b. 用户双击运行

1. 打开 `./output_dir/mineru/`
2. 双击 `run_extraction.bat`
3. 等待提取完成（CMD 窗口会显示进度）

### 1c. 告诉 OpenCode 提取完成

在 OpenCode 中输入："提取完成" 或 "extraction done"

## Step 2: 图片理解后处理（可选 Recommended if many images）

使用 Task 工具派出 `image-describer` 子智能体处理图片描述回填。

## Step 3: 分析课件结构

**两种类型 / Two Types:**

| 类型 Type | 适用课程 Typical Courses | 认知路径 Cognition Path |
|-----------|------------------------|------------------------|
| Traditional 传统分节式 | 物理、化学、材料科学 | 直觉类比 → 数学推导 → 物理意义 |
| Slide-based 幻灯片式 | CS、AI、工程类 | 问题/动机 → 核心机制 → 应用/意义 |

**检测信号 / Detection Signals:**

| 信号 Signal | Traditional | Slide-based |
|------------|-------------|-------------|
| 每页平均文本量 | 高（密集段落） | 低（标题+要点） |
| 章节编号 | 有明确 `## X.Y` | 无正式编号 |
| 页面间连贯性 | 强（段落延续） | 弱（每页自含） |

## Step 4: 编写讲义

### Traditional 模式模板

```markdown
# 第X节 标题

## 一、本节概述
（2-3句话，标注页码范围）

## 二、核心概念与推导（按课件页码顺序）
### 2.1 [课件P1] 标题
（直觉类比 → 数学推导 → 物理意义）

## 三、常见误区与辨析

## 四、考点总结

## 五、课件页码自查清单
| ✅ | 课件页码 | 讲义对应章节 | 核心内容 |
```

### Slide-Based 模式模板

```markdown
# Lecture XX: 标题（课件P1-P74）

## 一、本讲概述

## 二、Topic 1（课件P5-P25）
### [课件P5] 为什么需要...
### [课件P6-P8] 核心机制...

## 三、Topic 2（课件P26-P40）

## 四、常见误区与辨析

## 五、考点总结

## 六、课件页码自查清单
```

## Step 5: Review 迭代

**Review 循环 / Review Loop:**
```
round = 0
while True:
    round += 1
    ┌─ 子智能体Review（lecture-reviewer）
    │  输出：6维度评分 + Critical/Major/Minor建议
    │
    ├─ 终止条件 / Termination:
    │  ✅ 总评分 ≥ 8/10 且无Critical → 跳出
    │  ✅ round == 3 → 跳出
    │  ✅ 连续2轮无新见解 → 跳出
    │
    └─ 主智能体修改讲义（采纳建议）
```

**6 维度 / 6 Dimensions:**

| 维度 Dimension | 权重 Weight | 说明 |
|--------------|------------|------|
| 概念清晰度 | 25% | 新概念有清晰定义和类比 |
| 推导连贯性 | 20% | 每步可追溯，无跳步 |
| 逻辑衔接 | 15% | 段落/章节自然过渡 |
| 类比恰当性 | 10% | 贴近生活经验 |
| 页码顺序严格性 | 15% | 小节页码单调递增 |
| 自学对照友好度 | 15% | 学生能逐页对照 |

## Step 6: 上传 Notion（可选）

### 6.1 预检查 / Pre-check

```bash
python <notion_skill>/scripts/check_markdown_for_notion.py <markdown_file>
```

### 6.2 修复问题 / Fix Issues

**LaTeX pipe `|` 未转义** → 改列表格式
**表格 > 100 行** → 在合适位置插入 `---` 强制拆分

### 6.3 上传 / Upload

```bash
# 创建子页面
python <notion_skill>/scripts/archive_and_create_pages.py <parent_page_id> --titles "讲义_标题"

# 上传内容
python <notion_skill>/scripts/add_markdown_to_page.py <new_page_id> "lecture_notes.md"
```

## FAQ

**Q: MinerU 提取失败怎么办？**
A: 系统会自动回退到 `extract_pdf.py` 生成页面截图 + 逐页文字作为替代方案。

**Q: 图片很多怎么办？**
A: 使用 `image-describer` 子智能体对图片进行理解并回填到 Markdown。

**Q: PDF 超过 200 页怎么办？**
A: 使用 `split_pdf.py pre_split` 预切分，再分别提取后合并。

**Q: 如何判断用哪种模式（Traditional/Slide-based）？**
A: LLM 分析 `full_with_pages.md` 结构，根据每页文本量、章节编号、页面连贯性自动判断。

**Q: Review 可以跳过吗？**
A: 不可以。Review 是强制迭代过程，直到满足终止条件（总评分≥8/10 且无Critical 或 round==3）才进入下一步。

**Q: 可以不上传 Notion 吗？**
A: 可以。Notion 上传是可选步骤，讲义文件会保存在本地 `output_dir/` 目录。

---

[返回目录 / Back to README](../README.md)