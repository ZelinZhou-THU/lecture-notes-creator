---
name: notion
description: Notion API for creating and managing pages, databases, and blocks.
---

# notion

Use the Notion API to create/read/update pages, data sources (databases), and blocks.

## Setup

1. Create an integration at https://notion.so/my-integrations
2. Copy the API key (starts with `ntn_` or `secret_`)
3. Store it:

```bash
mkdir -p ~/.config/notion
echo "ntn_your_key_here" > ~/.config/notion/api_key
```

4. Share target pages/databases with your integration (click "..." → "Connect to" → your integration name)

## API Basics

All requests need:

```bash
NOTION_KEY=$(cat ~/.config/notion/api_key)
curl -X GET "https://api.notion.com/v1/..." \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json"
```

> **Note:** The `Notion-Version` header is required. This skill uses `2025-09-03` (latest). In this version, databases are called "data sources" in the API.

## Deleting Blocks - IMPORTANT SAFETY RULES

**⚠️ Deleting blocks is irreversible. Always follow these steps:**

### Before Deleting:
1. **Query first** - Always GET the blocks to see what's there before deciding what to delete
2. **Identify precisely** - Know exactly which block IDs are targets, never assume "delete all"
3. **Backup state** - Record the current block count and structure before making changes
4. **Small batch first** - Test delete 1-2 blocks first to verify you're targeting the right ones

### Deletion Command:
```bash
curl -X DELETE "https://api.notion.com/v1/blocks/{block_id}" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03"
```

### Safety Checklist:
- [ ] Did you GET the page content first to see all blocks?
- [ ] Did you identify specific block IDs to delete?
- [ ] Are you deleting ONLY the intended blocks (not all blocks)?
- [ ] Did you test with a small batch before full deletion?
- [ ] Do you have a way to restore if something goes wrong?

### Never Do:
- ❌ Don't delete all blocks from a page without checking what they are
- ❌ Don't assume you know what's in the page without querying first
- ❌ Don't use a loop that deletes without verifying each target
- ❌ Don't delete without having a restore plan

---

## Common Operations

**Search for pages and data sources:**

```bash
curl -X POST "https://api.notion.com/v1/search" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"query": "page title"}'
```

**Get page:**

```bash
curl "https://api.notion.com/v1/pages/{page_id}" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03"
```

**Get page content (blocks):**

```bash
curl "https://api.notion.com/v1/blocks/{page_id}/children" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03"
```

**Create page in a data source:**

```bash
curl -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"database_id": "xxx"},
    "properties": {
      "Name": {"title": [{"text": {"content": "New Item"}}]},
      "Status": {"select": {"name": "Todo"}}
    }
  }'
```

**Query a data source (database):**

```bash
curl -X POST "https://api.notion.com/v1/data_sources/{data_source_id}/query" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"property": "Status", "select": {"equals": "Active"}},
    "sorts": [{"property": "Date", "direction": "descending"}]
  }'
```

**Create a data source (database):**

```bash
curl -X POST "https://api.notion.com/v1/data_sources" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"page_id": "xxx"},
    "title": [{"text": {"content": "My Database"}}],
    "properties": {
      "Name": {"title": {}},
      "Status": {"select": {"options": [{"name": "Todo"}, {"name": "Done"}]}},
      "Date": {"date": {}}
    }
  }'
```

**Update page properties:**

```bash
curl -X PATCH "https://api.notion.com/v1/pages/{page_id}" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"properties": {"Status": {"select": {"name": "Done"}}}}'
```

**Add blocks to page:**

```bash
curl -X PATCH "https://api.notion.com/v1/blocks/{page_id}/children" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "children": [
      {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Hello"}, "annotations": {"bold": true}}]}}
    ]
  }'
```

> ⚠️ **Tip:** Use the `add_markdown_to_page.py` script instead of writing JSON manually. It handles all inline formatting (bold, italic, code) automatically.

## Property Types

Common property formats for database items:

- **Title:** `{"title": [{"text": {"content": "..."}}]}`
- **Rich text:** `{"rich_text": [{"text": {"content": "..."}}]}`
- **Select:** `{"select": {"name": "Option"}}`
- **Multi-select:** `{"multi_select": [{"name": "A"}, {"name": "B"}]}`
- **Date:** `{"date": {"start": "2024-01-15", "end": "2024-01-16"}}`
- **Checkbox:** `{"checkbox": true}`
- **Number:** `{"number": 42}`
- **URL:** `{"url": "https://..."}`
- **Email:** `{"email": "a@b.com"}`
- **Relation:** `{"relation": [{"id": "page_id"}]}`

## Key Differences in 2025-09-03

- **Databases → Data Sources:** Use `/data_sources/` endpoints for queries and retrieval
- **Two IDs:** Each database now has both a `database_id` and a `data_source_id`
  - Use `database_id` when creating pages (`parent: {"database_id": "..."}`)
  - Use `data_source_id` when querying (`POST /v1/data_sources/{id}/query`)
- **Search results:** Databases return as `"object": "data_source"` with their `data_source_id`
- **Parent in responses:** Pages show `parent.data_source_id` alongside `parent.database_id`
- **Finding the data_source_id:** Search for the database, or call `GET /v1/data_sources/{data_source_id}`

## Rich Text and Annotations

Notion supports inline formatting via annotations in rich_text objects:

```json
{
  "type": "text",
  "text": {"content": "bold text"},
  "annotations": {
    "bold": true,
    "italic": false,
    "strikethrough": false,
    "underline": false,
    "code": false,
    "color": "default"
}
```

For links: `"text": {"content": "link text", "link": {"url": "https://..."}}`

---

## Markdown to Notion Blocks Conversion

When adding markdown content to Notion, use this mapping:

| Markdown | Notion Block Type | Notes |
|----------|-------------------|-------|
| `# Title` | `heading_1` | Use `rich_text` with annotations |
| `## Title` | `heading_2` | Level 1-6 supported |
| `### Title` | `heading_3` | `####`, `#####`, `######` also work |
| `#### Title` | `heading_4` | Supported up to heading_6 |
| `- item` | `bulleted_list_item` | Use `rich_text` with annotations |
| `1. item` | `numbered_list_item` | Number auto-generated |
| `> quote` | `quote` | Block quote |
| `---` | `divider` | Horizontal rule |
| `` `code` `` | `paragraph` with `code: true` | Inline code via annotations |
| ` ```lang\ncode\n``` ` | `code` | Set `language` field |
| `<aside>...</aside>` | `callout` with emoji 💡 | Set `icon` and `color` |
| `![alt](url)` | `image` | External URL or file upload |
| `$$\nexpression\n$$` | `equation` | Math block |
| `$expression$` | `equation` in rich_text | Inline math (within text) |

### Inline Formatting in Rich Text

Parse these patterns and set annotations accordingly:
- `**text**` → `bold: true`
- `*text*` → `italic: true`
- `` `code` `` → `code: true`
- `~~text~~` → `strikethrough: true`
- `[text](url)` → `link` object
- `$expression$` → `{"type": "equation", "equation": {"expression": "..."}}` (inline math, **not** a rich_text object — a separate object type in the rich_text array)

### Inline Math (LaTeX)

Inline math `$...$` is automatically parsed by `parse_inline_formatting()`. It generates a Notion equation inline object:
```json
{"type": "equation", "equation": {"expression": "E(\\mathbf{k})"}}
```
This is different from block-level equations (`$$...$$`) which create standalone `equation` blocks. Inline equations are embedded within `rich_text` arrays alongside text objects.

**Important:** The `$...$` pattern must not be confused with currency. The parser treats any `$...$` with non-empty content as inline math.

### Numbered List Nesting

Numbered list items have special nesting behavior:
- **Bullet sub-items** after a numbered item are merged into the same `numbered_list_item`'s `rich_text` (separated by newlines) to prevent numbering reset
- **Indented code blocks** (````  ```lang ````) under a numbered item are added as `children` of the `numbered_list_item` block, rendering as properly formatted nested code
- In Notion, consecutive `numbered_list_item` blocks auto-number; inserting any other block type between them resets the count to 1

### Parser Implementation Pitfalls

When modifying `add_markdown_to_page.py`, be aware of these critical patterns:
- **Use `elif` chain, not `if`** — Each line type check must be `elif` (not `if`). Using `if` causes lines to match multiple conditions (e.g., a ` ``` ` line being added as both paragraph AND code block)
- **Use `continue` after multi-line blocks** — `aside`, `code`, `table`, and `numbered_list` all advance `i` internally. They must `continue` to skip the outer `i += 1`, otherwise lines get skipped or duplicated

### Table Handling

Tables require nested `table_row` children. Each row's cells is an array of rich_text arrays:

```json
{
  "type": "table",
  "table": {
    "table_width": 3,
    "has_column_header": true,
    "has_row_header": false,
    "children": [
      {"type": "table_row", "table_row": {"cells": [[{"type": "text", "text": {"content": "Header1"}}], [...], [...] ]}}
    ]
}
```

⚠️ **LaTeX pipe protection:** Table cells containing LaTeX `\|` (norm operator) are automatically protected before splitting on `|`. This prevents `\|\nabla\|` from being split into extra columns.

⚠️ **Table limitation:** You cannot append blocks to a page that already has a table block (validation error). Build table content in a separate script if needed.

### Upload Verification

After uploading, `add_markdown_to_page.py` automatically verifies the upload:
1. Compares block count on the Notion page vs. expected count
2. Reports chunk failures with explicit WARNING messages
3. If any chunks fail, prints which chunks failed and advises archiving + re-uploading

**When upload fails partially:**
- The script logs `WARNING: N/M chunks FAILED!` with failed chunk indices
- Remaining chunks may still upload, resulting in an incomplete page
- **Always** archive the incomplete page and re-upload from scratch (do not try to append missing blocks)

---

## Windows Terminal Encoding

On Windows PowerShell 5.1, Chinese characters may appear garbled in terminal output. This is a display-only issue — the Notion API data is correct.

**Solution (built-in):** All scripts automatically:
1. Set terminal codepage to UTF-8 (65001) via `chcp 65001`
2. Wrap `sys.stdout`/`sys.stderr` with UTF-8 encoding
3. Set `PYTHONIOENCODING=utf-8` environment variable

**If garbled output persists:**
- Write output to a JSON file with `ensure_ascii=False` and read it separately
- Use `repr()` or `.encode('ascii', 'backslashreplace')` to see Unicode code points
- The data is always correct in Python; only the terminal rendering is affected

---

## Page Management: Archive and Recreate

When a page needs to be cleared, **archive and recreate** is faster than deleting blocks one by one:

### Archive a page (soft delete):
```bash
curl -X PATCH "https://api.notion.com/v1/pages/{page_id}" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"archived": true}'
```

### Create new page:
```bash
curl -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"page_id": "parent_page_id"},
    "properties": {"title": {"title": [{"text": {"content": "New Page Title"}}]}}
  }'
```

---

## Content Modification Strategy

Choose the right approach based on your situation:

### Have local source files → Archive and Recreate
When you have the correct content locally (e.g., markdown files), the safest approach is to archive old pages and create new ones with fresh content. This avoids duplication and ensures clean formatting.

### Hot fix / in-page edit → Query, Target, Verify
When editing content that only exists on Notion (no local copy):
1. **GET** the page blocks first to see current state
2. **Identify** specific block IDs that need changes
3. **Modify** only those blocks (update, delete, or insert)
4. **Verify** the result before continuing
5. **Never** archive+recreate — you'd lose content with no backup

See `scripts/` directory for reusable tools:

| Script | Purpose |
|--------|---------|
| `_notion_utils.py` | Shared module: API helpers, formatting functions, constants (imported by all other scripts) |
| `add_markdown_to_page.py` | Parse generic markdown file and add formatted blocks to a Notion page |
| `import_notion_export.py` | Import Notion-exported markdown back to Notion with high fidelity (toggles, callouts, images, embeddings) |
| `export_page.py` | Export Notion page (with sub-pages and databases) to local Markdown/CSV files |
| `archive_and_create_pages.py` | Batch archive old pages and create new ones |
| `verify_page.py` | Verify page content and formatting stats |

### Two Import Scripts

- **`add_markdown_to_page.py`** — For generic Markdown files (blog posts, docs, READMEs). Broad format support, best-effort conversion.
- **`import_notion_export.py`** — For re-importing content exported by `export_page.py`. Preserves Notion-specific structures (toggles, callout emojis, image uploads, embeds, bookmarks). Use this for round-trip workflows.

### Usage Examples

**Add markdown to page (with proxy for China users):**
```bash
# Bash/Linux/Mac:
export HTTP_PROXY=http://127.0.0.1:<your_proxy_port>
export HTTPS_PROXY=http://127.0.0.1:<your_proxy_port>
python scripts/add_markdown_to_page.py <page_id> "path/to/guide.md"

# PowerShell (Windows):
$env:HTTP_PROXY = "http://127.0.0.1:<your_proxy_port>"
$env:HTTPS_PROXY = "http://127.0.0.1:<your_proxy_port>"
python scripts/add_markdown_to_page.py <page_id> "path/to/guide.md"
```

**Archive and recreate pages:**
```bash
python scripts/archive_and_create_pages.py <parent_id> old_ids.txt titles.txt
```

**Verify page formatting:**
```bash
python scripts/verify_page.py <page_id>
```

**Export page to local files:**
```bash
python scripts/export_page.py <page_id>
python scripts/export_page.py <page_id> --output ./my_export
python scripts/export_page.py <page_id> --no-assets --no-csv
```

**Import Notion export back to Notion:**
```bash
# Import a single exported page
python scripts/import_notion_export.py <page_id> "D:\Export\Page Title\index.md"

# Import with recursive sub-pages from directory
python scripts/import_notion_export.py <parent_page_id> "D:\Export\Page Title" --recursive
```

**Round-trip workflow (export → edit → re-import):**
```bash
# 1. Export
python scripts/export_page.py <page_id> --output ./backup

# 2. Edit the markdown files locally

# 3. Archive old pages and create new ones
python scripts/archive_and_create_pages.py <parent_id> old_ids.txt titles.txt

# 4. Re-import with high fidelity
python scripts/import_notion_export.py <new_page_id> "./backup/Page Title" --recursive
```

Export output structure:
```
Page Title/
├── index.md                  # Page content as markdown
├── assets/                   # Downloaded images/files
│   └── image.png
├── database_name.csv         # Database as CSV
├── Sub Page Title/
│   └── index.md              # Sub-page content (recursive)
└── Another Sub Page/
    └── index.md
```

These scripts handle:
- ✅ Inline formatting (bold, italic, code, strikethrough)
- ✅ **Inline math (`$...$` → equation inline objects in rich_text)**
- ✅ Code blocks with proper language
- ✅ Dividers, callouts, headings (H1-H6)
- ✅ Tables with proper structure (**including LaTeX `\|` pipe protection**)
- ✅ Numbered list nesting (sub-items + indented code blocks as children)
- ✅ Images (`![](url)` as external blocks or file uploads)
- ✅ Equations (`$$...$$` as equation blocks)
- ✅ Toggles, embeds, bookmarks (via `import_notion_export.py`)
- ✅ Proxy support (reads `HTTPS_PROXY`/`HTTP_PROXY` env vars)
- ✅ 50-block chunk uploads with retry logic (5 retries, exponential backoff)
- ✅ Rate limit handling (respects `Retry-After` header)
- ✅ **Upload verification (block count check after upload)**
- ✅ **Windows terminal UTF-8 encoding (auto codepage + PYTHONIOENCODING)**
- ✅ Full page export with sub-pages, databases (CSV + markdown), and asset downloads
- ✅ Round-trip import with toggle/callout/image reconstruction

---

## Proxy Configuration (China)

If Notion API is unreachable directly (common in China), configure a proxy.

**⚠️ Critical:** `add_markdown_to_page.py` and other scripts read proxy from **environment variables** `HTTP_PROXY` and `HTTPS_PROXY`. These MUST be set before running the scripts.

### Bash (Linux/Mac):
```bash
# 替换为你的代理端口，如 10808, 7890 等
export HTTPS_PROXY=http://127.0.0.1:<your_proxy_port>
export HTTP_PROXY=http://127.0.0.1:<your_proxy_port>
python scripts/add_markdown_to_page.py <page_id> "file.md"
```

### PowerShell (Windows):
```powershell
# 替换为你的代理端口
$env:HTTP_PROXY = "http://127.0.0.1:<your_proxy_port>"
$env:HTTPS_PROXY = "http://127.0.0.1:<your_proxy_port>"
python scripts/add_markdown_to_page.py <page_id> "file.md"
```

### Python scripts:
The `_notion_utils.py` module automatically reads these environment variables:
```python
# In _notion_utils.py
PROXIES = {"https": os.environ.get("HTTPS_PROXY", ""),
           "http": os.environ.get("HTTP_PROXY", "")}
```

If the environment variables are not set, scripts will attempt direct connection and may fail with `ConnectionResetError`.

### Custom proxy in Python:
```python
import requests
# 替换为你的代理端口
proxies = {"https": "http://127.0.0.1:<your_proxy_port>", "http": "http://127.0.0.1:<your_proxy_port>"}
requests.get(url, headers=headers, proxies=proxies)
```

---

## API Limitations

### Toggle Blocks

- You **cannot** create `child_page` blocks inside a toggle block via the API
- The `child_page` block type is read-only — it appears when you create subpages in the UI
- **Workaround:** Create subpages under the parent page instead of inside a toggle
- You CAN append other block types (paragraphs, headings, etc.) inside a toggle using `/blocks/{toggle_block_id}/children`

### Block Append Limits

- Use **50-block chunks** for reliable uploads, especially with unstable proxy connections
- Implement **retry logic** (3-5 retries with exponential backoff) for `429` and network errors
- Each append request can include up to 100 children, but smaller batches are more reliable

### Other Known Limitations

- Table blocks cannot be appended to a page that already has content (validation error) — add tables first or use a separate script
- Database view filters cannot be set via API — UI-only
- Rate limit: ~3 requests/second average, with `429 rate_limited` responses using `Retry-After`
- Payload size limits: up to 1000 block elements and 500KB overall

---

## Notes

- Page/database IDs are UUIDs (with or without dashes)
- Append block children: up to 100 children per request, up to two levels of nesting in a single append request
- Use `is_inline: true` when creating data sources to embed them in pages
