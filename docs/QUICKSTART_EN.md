# Quick Start Guide

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Lecture Notes Creator Workflow                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │  0. PDF      │    │  1. MinerU   │    │  2. OpenCode Auto        │  │
│  │  Analysis    │ -> │  Extraction  │ -> │  (Image→Analyze→Write)   │  │
│  │  (Optional)  │    │  (Run .bat)  │    │  + Review Loop           │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘  │
│                                                   │                      │
│                                                   v                      │
│                      ┌──────────────────────────────────────────────┐    │
│                      │         3. Upload to Notion (Optional)       │    │
│                      └──────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘

Detailed Steps:

Step 0: PDF Analysis
    └─ split_pdf.py analyze → determine if splitting is needed

Step 1: MinerU Extraction
    └─ create_extraction_bat.py → generates .bat file
    └─ User double-clicks to run

Step 2-5: OpenCode Automatic Processing
    ├─ 2. Image understanding (image-describer sub-agent)
    ├─ 3. Analyze courseware structure
    ├─ 4. Write lecture notes
    └─ 5. Review iterations

Step 6: Upload to Notion (Optional)
    └─ check_markdown_for_notion.py → add_markdown_to_page.py
```

## Step 0: PDF Analysis (Optional, only if >200 pages)

```bash
python scripts/split_pdf.py analyze "path/to/courseware.pdf" --preview 3
```

**Decision Logic:**
- ≤200 pages → skip to Step 1
- >200 pages → run pre-split, extract separately, then merge

## Step 1: MinerU Extraction

### 1a. Generate .bat file (Recommended)

```bash
python scripts/create_extraction_bat.py "path/to/courseware.pdf" --output ./output_dir/mineru --mode auto
```

- `--mode vlm` (default, recommended): high precision, best for formula-dense and complex tables
- `--mode pipeline`: fast mode, suitable for plain text / simple layouts

> **Why generate a .bat file instead of running directly?**
> OpenCode's terminal can freeze when detecting heavy I/O operations (e.g., MinerU batch file downloads/deletions). The solution is: generate .bat → user double-clicks to run → user tells OpenCode when done.

### 1b. User double-clicks to run

1. Open `./output_dir/mineru/`
2. Double-click `run_extraction.bat`
3. Wait for extraction to complete (CMD window shows progress)

### 1c. Tell OpenCode extraction is done

Type in OpenCode: `"extraction done"`

## Step 2: Image Understanding (Optional, recommended for image-heavy PDFs)

Use the Task tool to dispatch the `image-describer` sub-agent for batch image description.

## Step 3: Analyze Courseware Structure

**Two Types:**

| Type | Typical Courses | Cognition Path |
|------|----------------|----------------|
| Traditional | Physics, Chemistry, Materials Science | Analogy → Derivation → Meaning |
| Slide-based | CS, AI, Engineering | Problem/Motivation → Mechanism → Application |

**Detection Signals:**

| Signal | Traditional | Slide-based |
|--------|-------------|-------------|
| Text per page | High (dense paragraphs) | Low (headings + bullets) |
| Section numbering | Explicit `## X.Y` | No formal numbering |
| Page coherence | Strong (paragraphs continue) | Weak (each page self-contained) |

## Step 4: Write Lecture Notes

### Traditional Mode Template

```markdown
# Section X Title

## 1. Overview
(2-3 sentences, note page range)

## 2. Core Concepts & Derivation (in page order)
### 2.1 [Slide P1] Title
(Analogy → Derivation → Meaning)

## 3. Common Misconceptions

## 4. Exam Key Points

## 5. Page Coverage Checklist
| ✅ | Slide Page | Section | Core Content |
```

### Slide-Based Mode Template

```markdown
# Lecture XX: Title (Slides P1-P74)

## 1. Overview

## 2. Topic 1 (Slides P5-P25)
### [Slide P5] Why do we need...
### [Slide P6-P8] Core mechanism...

## 3. Topic 2 (Slides P26-P40)

## 4. Common Misconceptions

## 5. Exam Key Points

## 6. Page Coverage Checklist
```

## Step 5: Review Iteration

**Review Loop:**
```
round = 0
while True:
    round += 1
    ┌─ Sub-agent Review (lecture-reviewer)
    │  Output: 7-dimension score + Critical/Major/Minor suggestions
    │
    ├─ Termination:
    │  ✅ Score ≥ 8/10 and no Critical → exit
    │  ✅ round == 3 → exit
    │  ✅ No new insights for 2 consecutive rounds → exit
    │
    └─ Main agent revises notes (applies suggestions)
```

**7 Dimensions:**

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Concept Clarity | 20% | Clear definitions and analogies |
| Derivation Coherence | 15% | Every step traceable, no jumps |
| Logical Flow | 10% | Natural transitions between sections |
| Analogy Appropriateness | 10% | Close to everyday experience |
| Page Order Strictness | 10% | Page numbers strictly increasing |
| Self-Study Friendliness | 10% | Students can follow page by page |
| Content Accuracy | 25% | Faithful to original courseware |

## Step 6: Upload to Notion (Optional)

### 6.1 Pre-check

```bash
python <notion_skill>/scripts/check_markdown_for_notion.py <markdown_file>
```

### 6.2 Fix Issues

**LaTeX pipe `|` not escaped** → change to list format
**Table > 100 rows** → insert `---` at appropriate positions to force split

### 6.3 Upload

```bash
# Create sub-page
python <notion_skill>/scripts/archive_and_create_pages.py <parent_page_id> --titles "Notes_Title"

# Upload content
python <notion_skill>/scripts/add_markdown_to_page.py <new_page_id> "lecture_notes.md"
```

## FAQ

**Q: What if MinerU extraction fails?**
A: The system automatically falls back to `extract_pdf.py` for page screenshots + per-page text extraction.

**Q: What if the PDF has many images?**
A: Use the `image-describer` sub-agent to batch-understand images and backfill descriptions into the Markdown.

**Q: What if the PDF exceeds 200 pages?**
A: Use `split_pdf.py pre_split` to pre-split, extract each part separately, then merge.

**Q: How to determine Traditional vs Slide-based mode?**
A: The LLM analyzes `full_with_pages.md` structure and auto-detects based on text density, section numbering, and page coherence.

**Q: Can I skip the Review step?**
A: No. Review is mandatory and iterates until termination conditions are met (score ≥ 8/10 with no Critical items, or round == 3).

**Q: Can I skip Notion upload?**
A: Yes. Notion upload is optional. Notes are always saved locally in the `output_dir/` directory.

---

[Back to README](../README.md)
