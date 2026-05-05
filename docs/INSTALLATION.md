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
git clone https://github.com/your-repo/lecture-notes-creator.git
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

### Install notion skill 安装 notion skill

```bash
# 确认 notion skill 已安装 / Verify notion skill is installed
skill list | grep notion
```

### Get Notion API Key 获取 Notion API Key

1. 访问 Visit [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. 创建新集成 / Create new integration
3. 选择要访问的工作区 / Select workspace to access
4. 复制 API Key / Copy API Key
5. 在 Notion 页面中添加集成 / Add integration to Notion page

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