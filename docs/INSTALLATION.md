# Installation Guide 安装指南

## System Requirements 系统要求

| Component 组件 | Requirement 要求 |
|---------------|-----------------|
| Python | 3.10+ |
| OS | Windows 10+, macOS, Linux |
| Memory 内存 | 8GB+ RAM（推荐 Recommended） |
| Disk Space 磁盘空间 | 2GB+ free space 空闲空间 |

## Installation Steps 安装步骤

### Step 1: Clone the repository 克隆仓库

```bash
git clone https://github.com/ZelinZHOU-THU/lecture-notes-creator.git
cd lecture-notes-creator
```

### Step 2: Install dependencies 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖 / Main dependencies:
- `requests` - MinerU API 调用 / MinerU API calls
- `pypdf` - PDF 预切分 / PDF pre-splitting
- `pdfplumber` - 页面截图 + fallback 文字提取 / page screenshots + fallback text extraction
- `pdf2image` - PDF 转图片 / PDF to images

### Step 3: Configure API Keys 配置 API Keys

Create `.env` file in project root 在项目根目录创建 `.env` 文件：

```env
# MinerU API Key（必须 Required）- 从 https://mineru.net/ 获取
MINERU_TOKEN=your_mineru_api_key_here

# Notion API Key（可选 Optional）- 从 https://www.notion.so/my-integrations 获取
NOTION_API_KEY=your_notion_api_key_here
```

## Get MinerU API Key 获取 MinerU API Key

1. 访问 Visit [mineru.net](https://mineru.net/)
2. 注册账号 / Register an account
3. 进入控制台 / Go to dashboard
4. 创建 API Key / Create API Key
5. 复制 Key 到 `.env` 文件 / Copy Key to `.env` file

**限制 / Limits:**
- 单文件 ≤ 200MB, ≤ 200 页 / pages
- 每天前 1000 页高优先级 / first 1000 pages high priority daily
- presigned URL 有效期 24 小时 / 24-hour validity

## Configure Notion（可选 Optional）

### Notion skill 已内置

Notion skill 已内置在 `deps/notion/` 目录，无需额外安装。

### Get Notion API Key 获取 Notion API Key

1. 访问 Visit [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. 创建新集成 / Create new integration
3. 选择要访问的工作区 / Select workspace to access
4. 复制 API Key / Copy API Key
5. 在 Notion 页面中添加集成 / Add integration to Notion page

### Configure Proxy（可选 Optional，中国用户可能需要）

Notion API 在某些地区可能无法直接访问，如遇到连接失败，可配置代理。

**Bash/Linux/Mac:**
```bash
export HTTP_PROXY=http://127.0.0.1:<your_proxy_port>
export HTTPS_PROXY=http://127.0.0.1:<your_proxy_port>
```

**PowerShell (Windows):**
```powershell
$env:HTTP_PROXY = "http://127.0.0.1:<your_proxy_port>"
$env:HTTPS_PROXY = "http://127.0.0.1:<your_proxy_port>"
```

**常见代理端口 / Common proxy ports:**
- Clash: 7890
- V2Ray: 10808
- Shadowsocks: 1080

脚本会自动读取 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量。

## Configure Subagents（配置子智能体）

本 skill 使用两个子智能体：
- `lecture-reviewer`：以本科生视角review讲义质量（7维度评分）
- `image-describer`：对课件图片进行批量理解和描述

### 注册方法

有两种配置方式，推荐方式一：

**方式一：opencode.json 在项目目录（推荐）**

在 `lecture-notes-creator` 项目根目录创建 `.opencode.json`：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "lecture-reviewer": {
      "description": "以本科生自学视角review讲义质量，7维度评分+Critical/Major/Minor建议",
      "mode": "subagent",
      "model": "<your-model>",
      "temperature": 0.4,
      "hidden": true,
      "prompt": "{file:.opencode/agents/lecture-reviewer.md}",
      "permission": {
        "edit": "deny",
        "bash": "deny"
      }
    },
    "image-describer": {
      "description": "对 MinerU 提取的课件图片进行批量理解，生成描述并回填到 Markdown",
      "mode": "subagent",
      "model": "<your-model>",
      "temperature": 0.3,
      "hidden": true,
      "prompt": "{file:.opencode/agents/image-describer.md}",
      "permission": {
        "edit": "deny",
        "bash": "allow"
      }
    }
  }
}
```

**方式二：opencode.json 在全局配置目录**

如果你的 opencode.json 在 `~/.opencode/config.json`，需要将 `{file:.opencode/agents/...}` 替换为绝对路径：

```json
{
  "prompt": "{file:/absolute/path/to/lecture-notes-creator/.opencode/agents/lecture-reviewer.md}"
}
```

**注意：** 将 `/absolute/path/to/lecture-notes-creator` 替换为你实际的项目路径。

### Model 选择

将 `<your-model>` 替换为你使用的模型，常见选项：

**lecture-reviewer（讲义 Review）：**
- **免费/低成本模型**：`gpt-4o-mini`、`claude-3-5-haiku`、`qwen-turbo`、`deepseek-chat`、`moonshot-v1-8k`
- **高端模型**（推荐）：`gpt-4o`、`claude-3-5-sonnet`、`claude-3-5-opus`、`gemini-2.0-flash`

**image-describer（图片理解）：**
- **说明**：此子智能体主要通过 MCP 工具调用视觉理解 API（如 `zai-mcp-server_analyze_image`），model 字段影响较小
- **推荐**：使用免费/低成本模型即可（如 `gpt-4o-mini`），主要工作由 MCP 完成
- **MCP 依赖**：需要配置视觉理解 MCP（如 Zhipu AI、OpenAI Vision API 等）

**常见 MCP 视觉接口：**
- `zai-mcp-server_analyze_image`（视觉理解）
- MinerU 内置的多模态接口
- OpenAI GPT-4o（Vision）
- Anthropic Claude（Vision）

**注意事项：**
- `temperature` 已优化，建议保持默认值
- 子智能体配置文件已内置在 `.opencode/agents/` 目录

### 验证注册

运行以下命令验证子智能体是否正确注册：

```bash
# 查看已注册的子智能体
opencode agent list
```

应该能看到 `lecture-reviewer` 和 `image-describer`。

## Verify Installation 验证安装

```bash
python scripts/mineru_extract.py --help
python scripts/split_pdf.py --help
```

输出帮助信息表示安装成功 / Output of help message indicates successful installation.

## Dependencies Table 依赖表

| Package 包 | Version 版本 | Purpose 用途 |
|-----------|-------------|-------------|
| requests | >= 2.28 | HTTP 请求 / HTTP requests |
| pypdf | >= 4.0 | PDF 读取 / PDF reading |
| pdfplumber | >= 0.10 | 表格提取 / Table extraction |
| pdf2image | >= 1.16 | PDF 转图片 / PDF to images |
| python-dotenv | >= 1.0 | 环境变量 / Environment variables |
| pillow | >= 10.0 | 图片处理 / Image processing |

All dependencies are automatically installed via `requirements.txt`.

所有依赖通过 `requirements.txt` 自动安装。