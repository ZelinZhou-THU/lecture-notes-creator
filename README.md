# Lecture Notes Creator 讲义生成器

将晦涩的学术课件（PDF）转化为易懂的本科生自学讲义（Markdown），含子智能体 review 迭代和 Notion 上传。

## 核心功能

- **MinerU API 高质量提取**：使用 MinerU v4 API（默认 VLM 模式）从 PDF 中提取文字、公式、表格、图片，公式 LaTeX 化、表格 HTML 化，完美保留课件内容
- **页码驱动结构**：讲义严格按课件页码顺序组织（P1→P2→P3→...），每页必现，方便学生逐页对照自学
- **两种课件类型自适应**：
  - **传统分节式**（物理、化学、材料科学等）：直觉类比 → 数学推导 → 物理意义
  - **幻灯片式**（CS、AI、工程类等）：问题/动机 → 核心机制 → 应用/意义
- **子智能体 AI Review 迭代**：每章讲义完成后由子智能体以本科生视角 review，7维度评分 + 迭代优化，直到达标才进入下一步
- **Notion 云端同步**：讲义可上传至 Notion 知识库，与课程学习页面集成

## 快速开始

> 📌 **完整安装指南**：详细的安装步骤、API Key 配置、代理设置、子智能体注册请参考 [INSTALLATION.md](docs/INSTALLATION.md)

### 前置条件

- Python 3.10+
- MinerU API Key（从 [mineru.net](https://mineru.net/) 获取）
- （可选）Notion API Key

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/ZelinZHOU-THU/lecture-notes-creator.git
   cd lecture-notes-creator
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置 API Key**
   在项目根目录创建 `.env` 文件：
   ```env
   MINERU_TOKEN=your_mineru_api_key_here
   NOTION_API_KEY=your_notion_api_key_here  # 可选
   ```

4. **验证安装**
   ```bash
   python scripts/mineru_extract.py --help
   ```

### 基本用法

1. **分析 PDF**（可选，超过 200 页才需要切分）
   ```bash
   python scripts/split_pdf.py analyze "path/to/courseware.pdf" --preview 3
   ```

2. **MinerU 提取**（生成 .bat 文件，用户双击运行）
   ```bash
   python scripts/create_extraction_bat.py "path/to/courseware.pdf" --output ./output_dir/mineru --mode auto
   ```

3. **告诉 OpenCode "提取完成"**，OpenCode 检查状态后继续

4. **子智能体分析图片**（可选，图片多时建议）
   - 使用 Task 工具派出 `image-describer` 子智能体

5. **分析课件结构**
   - 识别课件类型（traditional / slide-based）
   - traditional 类型：按章节组织
   - slide-based 类型：LLM 自动聚类主题

6. **编写讲义**
   - 按页码顺序严格编写
   - 每章完成后子智能体 review 迭代

7. **上传到 Notion**（可选）
   ```bash
   python <notion_skill>/scripts/check_markdown_for_notion.py <markdown_file>
   # 修复问题后
   python <notion_skill>/scripts/add_markdown_to_page.py <page_id> "lecture_notes.md"
   ```

## 项目结构

```
lecture-notes-creator/
├── SKILL.md                     # 技能定义文件
├── README.md                    # 本文件（中文）
├── README_EN.md                 # 英文版 README
├── LICENSE                      # MIT License
├── NOTICE                       # 致谢和开源组件
├── .gitignore                   # Git 忽略规则
├── .env                         # API Key 配置（需手动创建）
 ├── .opencode/
 │   └── agents/
 │       ├── lecture-reviewer.md  # 子智能体：讲义 Review（需在 opencode.json 中注册）
 │       └── image-describer.md   # 子智能体：图片理解（需在 opencode.json 中注册）
├── docs/
│   ├── INSTALLATION.md          # 安装指南（中英双语）
│   └── QUICKSTART.md            # 快速开始（中英双语）
├── scripts/
│   ├── split_pdf.py             # PDF 分析/预切分/合并
│   ├── extract_pdf.py           # 页面截图（fallback 方案）
│   ├── mineru_extract.py        # MinerU API 调用
│   ├── create_extraction_bat.py # 生成 .bat 文件（双击运行）
│   ├── reconstruct_full_md.py  # 从 JSON 重建 Markdown
│   ├── backfill_image_descriptions.py  # 图片描述回填
│   ├── save_batch_json.py       # 增量保存图片描述 JSON
│   └── wait_for_extraction.py   # 等待 MinerU 完成
└── references/
    ├── writing-style-guide.md   # 讲义写作风格指南
    └── review-prompt.md         # Review 提示词模板（备份）
```

## Credits

本项目基于以下开源组件构建：

- **MinerU**：高保真 PDF 内容提取工具，Modified Apache License 2.0
  - 仓库：https://github.com/opendatalab/MinerU
- **notion skill**（来自 OpenClaw，已内置在 `deps/notion/`）：Notion API 集成，MIT License
  - 仓库：https://github.com/openclaw/openclaw/tree/main/skills/notion
- **MinerU skill**（来自 LobeHub，已内置在 `deps/mineru/`）：技能封装参考，MIT License
  - 仓库：https://lobehub.com/zh/skills/openclaw-skills-mineru

## License

Apache License 2.0