# Notion Upload Guide

## Prerequisites

- All chapter Review iterations must be complete before uploading.
- `NOTION_API_KEY` must be set in `.env`.

## Step 6.0 — Confirm Upload

Ask the user:
> **Upload to Notion?**
> - `y` / `yes`: continue
> - `n` / `no`: skip, workflow ends

If no: output "Workflow complete (Notion upload skipped)" and end.

## Step 6.1 — Table Pre-check

Run before upload to detect three types of issues:

```bash
python deps/notion/scripts/check_markdown_for_notion.py <markdown_file>
```

**Detection items:**
1. **LaTeX pipe `|` not escaped** — formulas with `|` (e.g. `$\hat{p}(y|x)$`) break table column parsing
2. **Row cell count mismatch** — header and body column counts differ
3. **Table > 100 rows** — Notion API limits table block children to 100 rows

Fix all issues before proceeding.

## Step 6.2 — Table Fix Rules

**1. LaTeX pipe cells → list format**

```markdown
# Bad:
| Method | Formula |
|--------|---------|
| Imitation | Learn $\hat{p}(y|x)$ |

# Good:
**Imitation**: Learn $p(y|x)$, description...
```

**2. Coverage table > 100 rows → split with `---`**

Insert `---` horizontal rule at ~row 50 (or a natural semantic break):

```markdown
| ✅ | Page | Section | Content |
|---|------|---------|---------|
| [ ] | P1 | ... | ... |
| [ ] | P50 | ... | ... |

---

| ✅ | Page | Section | Content |
|---|------|---------|---------|
| [ ] | P51 | ... | ... |
```

This creates two separate table blocks, each under 100 rows.

## Step 6.3 — Upload Flow

1. **Find parent page**: Search Notion API for the parent page (e.g. "课程学习" or user-specified name), confirm `page_id`
2. **Find or create course page**: Check if the course (e.g. "Solid State Physics") exists as a sub-page; create if not
3. **Find or create chapter page**: Check or create chapter sub-page (e.g. "Chapter 4")
4. **Upload notes**: Use `add_markdown_to_page.py` to upload each note file as a sub-page
5. **Upload exam summary**: Upload as a separate sub-page under the chapter

**Page hierarchy (example — customize per user):**
```
Parent Page (existing)
└── Course Name (find/create)
    └── Chapter (find/create)
        ├── Notes_4.9_DOS (upload)
        ├── Notes_4.10_Low_Dim (upload)
        └── Notes_Ch4_Exam_Summary (upload)
```

**Upload commands:**
```bash
# Create sub-page
python deps/notion/scripts/archive_and_create_pages.py <parent_page_id> --titles "Notes_4.9_DOS"

# Upload content
python deps/notion/scripts/add_markdown_to_page.py <new_page_id> "Notes_4.9_DOS.md"
```

**Built-in Notion scripts:** All scripts are in `deps/notion/scripts/`. Scripts auto-read `NOTION_API_KEY` from `.env`. For proxy, set `HTTP_PROXY` / `HTTPS_PROXY` environment variables.
