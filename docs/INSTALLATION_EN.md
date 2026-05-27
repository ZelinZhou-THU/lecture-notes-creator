# Installation Guide

## System Requirements

| Component | Requirement |
|-----------|-------------|
| Python | 3.10+ |
| OS | Windows 10+, macOS, Linux |
| Memory | 8GB+ RAM (Recommended) |
| Disk Space | 2GB+ free space |

### OpenCode

This skill runs inside [OpenCode](https://opencode.ai) — an AI-powered coding assistant. Install it by following the guide at [opencode.ai](https://opencode.ai), then open this project in OpenCode to start.

### System Dependencies

The `pdf2image` package requires `poppler` to be installed on your system:
- **Windows**: Download [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases), extract, and add the `bin/` directory to your PATH
- **macOS**: `brew install poppler`
- **Linux**: `sudo apt install poppler-utils`

## Installation Steps

### Step 1: Clone the repository

```bash
git clone https://github.com/ZelinZhou-THU/lecture-notes-creator.git
cd lecture-notes-creator
```

### Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

Main dependencies:
- `requests` — MinerU API calls
- `pypdf` — PDF pre-splitting
- `pdfplumber` — Page screenshots + fallback text extraction
- `pdf2image` — PDF to images

### Step 3: Configure API Keys

Create `.env` file in project root:

```env
# MinerU API Key (Required) - get from https://mineru.net/
MINERU_TOKEN=your_mineru_api_key_here

# Notion API Key (Optional) - get from https://www.notion.so/my-integrations
NOTION_API_KEY=your_notion_api_key_here
```

## Get MinerU API Key

1. Visit [mineru.net](https://mineru.net/)
2. Register an account
3. Go to dashboard
4. Create API Key
5. Copy Key to `.env` file

**Limits:**
- Single file ≤ 200MB, ≤ 200 pages
- First 1000 pages high priority daily
- Presigned URL valid for 24 hours

## Configure Notion (Optional)

### Notion skill included

The Notion skill is bundled in `deps/notion/`, no extra installation needed.

### Get Notion API Key

1. Visit [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Create new integration
3. Select workspace to access
4. Copy API Key
5. Add integration to your Notion page

### Configure Proxy (Optional, recommended for users in China)

If the Notion API is not accessible from your region, configure a proxy:

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

**Common proxy ports:**
- Clash: 7890
- V2Ray: 10808
- Shadowsocks: 1080

All scripts automatically read `HTTP_PROXY` and `HTTPS_PROXY` environment variables.

## Configure Subagents

This skill uses two subagents:
- `lecture-reviewer`: Reviews lecture notes from an undergraduate perspective (7-dimension scoring)
- `image-describer`: Batch image understanding and description

### Registration

Two configuration methods. Method 1 is recommended:

**Method 1: opencode.json in project directory (Recommended)**

Create `.opencode.json` in the `lecture-notes-creator` root:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "lecture-reviewer": {
      "description": "Reviews lecture notes quality from an undergraduate self-study perspective",
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
      "description": "Batch image understanding for courseware images",
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

**Method 2: opencode.json in global config directory**

If your opencode.json is at `~/.opencode/config.json`, replace `{file:.opencode/agents/...}` with absolute paths:

```json
{
  "prompt": "{file:/absolute/path/to/lecture-notes-creator/.opencode/agents/lecture-reviewer.md}"
}
```

### Model Selection

Replace `<your-model>` with your chosen model:

**lecture-reviewer (notes review):**
- **Free/low-cost models**: `gpt-4o-mini`, `claude-3-5-haiku`, `qwen-turbo`, `deepseek-chat`, `moonshot-v1-8k`
- **Premium models** (recommended): `gpt-4o`, `claude-3-5-sonnet`, `claude-3-5-opus`, `gemini-2.0-flash`

**image-describer (image understanding):**
- This subagent primarily uses MCP tools for vision APIs (e.g., `zai-mcp-server_analyze_image`), so the model field has less impact
- Recommended: use free/low-cost models (e.g., `gpt-4o-mini`)
- Requires a vision-enabled MCP server

**Common MCP vision interfaces:**
- `zai-mcp-server_analyze_image`
- OpenAI GPT-4o (Vision)
- Anthropic Claude (Vision)

**Notes:**
- `temperature` values are already optimized; keep the defaults
- Subagent config files are bundled in `.opencode/agents/`

### Verify Registration

```bash
opencode agent list
```

You should see both `lecture-reviewer` and `image-describer`.

## Verify Installation

```bash
python scripts/mineru_extract.py --help
python scripts/split_pdf.py --help
```

If help messages display, installation is successful.

## Dependencies Table

| Package | Version | Purpose |
|---------|---------|---------|
| requests | >= 2.28 | HTTP requests |
| pypdf | >= 4.0 | PDF reading |
| pdfplumber | >= 0.10 | Table extraction |
| pdf2image | >= 1.16 | PDF to images |
| python-dotenv | >= 1.0 | Environment variables |
| pillow | >= 10.0 | Image processing |
| psutil | >= 5.9 | System monitoring |

All dependencies are automatically installed via `requirements.txt`.
