---
name: lecture-notes-creator
description: "Transform course PDFs into page-by-page self-study lecture notes (Markdown) with AI review and optional Notion upload. Supports two courseware types: (1) Traditional section-based (physics/chemistry) with analogy→derivation→meaning path; (2) Slide-based (CS/AI) with problem→mechanism→application path. Uses MinerU API for high-fidelity extraction (VLM mode). Triggers: lecture notes, course notes, exam prep, 讲义, 课件讲解, 考点总结, 课程笔记, 从课件生成讲义, 分析课件, 上传讲义到Notion."
---

# Lecture Notes Creator

Transform dense course PDFs into clear self-study notes with iterative AI review and optional Notion upload.

## Language Rule

Notes follow the courseware's original language (English PDF → English notes, Chinese PDF → Chinese notes). User can explicitly specify a different language. Key terms annotate the opposite language on first occurrence.

## Setup

### Prerequisites

- Python 3.10+, [OpenCode](https://opencode.ai) installed
- System: `poppler` (see [INSTALLATION.md](docs/INSTALLATION.md) for platform-specific steps)
- API Keys: MinerU (required, from [mineru.net](https://mineru.net)), Notion (optional)

### Install

```bash
git clone https://github.com/ZelinZhou-THU/lecture-notes-creator.git
cd lecture-notes-creator
pip install -r requirements.txt
```

Create `.env` in project root:

```env
MINERU_TOKEN=your_key_here
NOTION_API_KEY=your_key_here   # optional
```

### Register Subagents

Create `.opencode.json` in project root. Replace `<your-model>` with your model name.

```json
{
  "agent": {
    "lecture-reviewer": {
      "mode": "subagent", "model": "<your-model>", "temperature": 0.4, "hidden": true,
      "prompt": "{file:.opencode/agents/lecture-reviewer.md}",
      "permission": { "edit": "deny", "bash": "deny" }
    },
    "image-describer": {
      "mode": "subagent", "model": "<your-model>", "temperature": 0.3, "hidden": true,
      "prompt": "{file:.opencode/agents/image-describer.md}",
      "permission": { "edit": "deny", "bash": "allow" }
    }
  }
}
```

For detailed guide (proxy, MCP, model selection), see [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Workflow

### 0. Preparation & Splitting (for long PDFs)

Needed when PDF exceeds MinerU's 200-page limit or LLM context length.

#### 0a. Analyze PDF

```bash
python scripts/split_pdf.py analyze "path/to/courseware.pdf" --preview 3
```

Output: total pages, file size, whether pre-split is needed, TOC detection, text preview.

**Logic:** ≤200 pages → Step 1; >200 pages → Step 0b, then MinerU per chunk + merge.

#### 0b. Pre-split Large PDF (>200 pages)

```bash
python scripts/split_pdf.py pre_split "input.pdf" --output ./pre_split --chunk-size 150
```

Then MinerU extract each chunk and merge:

```bash
python scripts/split_pdf.py merge_md ./chunk1_mineru/full.md ./chunk2_mineru/full.md --output ./mineru/full.md
```

Image paths are auto-consolidated into a unified `images/` directory.

#### 0c. Courseware Type Detection

After MinerU produces `full_with_pages.md`, **detect courseware type** before proceeding.

**LLM analyzes `full_with_pages.md` structure:**

| Signal | Traditional (section-based) | Slide-based |
|--------|----------------------------|-------------|
| Text per page | High (dense paragraphs) | Low (headings + bullets) |
| Section numbering | Explicit `## X.Y` headers | No formal numbering |
| Page coherence | Strong (paragraphs continue) | Weak (each page self-contained) |
| Typical courses | Physics, Chemistry, Materials | CS, AI, Engineering |

Output:
```json
{
  "courseware_type": "traditional" | "slide-based"
}
```

---

#### 0d-traditional. Split Markdown by Section (traditional only)

**Prerequisite: `courseware_type == "traditional"`**

For long chapters, physically split into section files:

```bash
python scripts/split_pdf.py split_md ./mineru/full_with_pages.md --plan split_plan.json --output ./sections
```

Split plan format (LLM-generated):
```json
{
  "sections": [
    {"heading": "# 4.1", "start_marker": null, "title": "4.0_Prelude+4.1"},
    {"heading": "# 4.2", "start_marker": "# 4.2", "title": "4.2_Bloch_Theorem"},
    {"heading": "# 4.3", "start_marker": "# 4.3", "title": "4.3_Nearly_Free_Electrons"}
  ]
}
```

**`start_marker` rules:**
- **First section**: `null` or `""` → start from file beginning
- **Subsequent sections**: must be a concrete string (e.g. `"# 4.2"`) to locate the Markdown heading line. Empty values cause the section to be skipped.

**Mixed strategy**: Short sections (<30 pages) can be read directly from `full.md`. Only long sections need physical splitting.

---

#### 0d-slide. Topic Clustering (slide-based only)

**Prerequisite: `courseware_type == "slide-based"`**

LLM reads `full_with_pages.md` and clusters consecutive slides into Topics:

1. Scan pages, identify topic boundaries (title meaning changes, new concepts, theory→application shifts)
2. Group consecutive related pages into Topics
3. Each Topic needs a clear title and page range

Output **Topic Map** (JSON):
```json
{
  "courseware_type": "slide-based",
  "topics": [
    {"title": "Self-Attention Mechanism", "page_range": [5, 25]},
    {"title": "Multi-Head Attention", "page_range": [26, 40]},
    {"title": "Positional Encoding", "page_range": [41, 55]},
    {"title": "Full Transformer Architecture", "page_range": [56, 74]}
  ]
}
```

**Clustering rules:**
- Each Topic = one complete concept/subtopic
- Pages within a Topic must be consecutive
- Single Topic should not exceed 30 pages
- Titles follow the courseware's language, with key terms in both languages

### 1. Extract Courseware Content

#### 1a. MinerU High-Fidelity Extraction (primary, user-run mode)

**Important: To avoid OpenCode memory leaks, MinerU extraction must run outside OpenCode.**

**Workflow:**

1. **OpenCode generates extraction script** (one-time):
   ```bash
   python scripts/create_extraction_bat.py "path/to/courseware.pdf" --output ./output_dir/mineru --mode auto
   ```

2. **User runs the generated script** (double-click `.bat` on Windows, or run `.sh` on macOS/Linux)

3. **User tells OpenCode extraction is done**: input "extraction done" or "提取完成"

4. **OpenCode continues**: read `full_with_pages.md`, write notes, Review, Notion upload

**Output files:**
- `output_dir/mineru/full.md` (raw Markdown, no page numbers)
- `output_dir/mineru/full_with_pages.md` (with `> [Page P{N}]` annotations per content block)
- `output_dir/mineru/images/` (extracted images)
- `output_dir/mineru/extraction_status.json` (status tracking)

**Token config**: Set `MINERU_TOKEN=your_key` in `.env` (get from https://mineru.net/).

**Mode options:** `--mode vlm` (default, recommended), `--mode pipeline` (fast), `--mode auto` (= vlm)

#### 1b. Page Screenshots (fallback when MinerU fails)

```bash
python scripts/extract_pdf.py "path/to/courseware.pdf" --output ./output_dir --dpi 200
```

Output: `output_dir/images/page_NN.png` + `output_dir/summary.txt`.

Only needed when MinerU fails. Generates page screenshots + per-page text as fallback.

#### 1c. Image Understanding Post-processing (optional)

> When the courseware contains many images (diagrams, flowcharts, experimental results), execute this step. MinerU-extracted images are already renamed `img_001.jpg` ~ `img_NNN.jpg`, but their internal structure cannot be understood from filenames alone. This step generates text descriptions via multimodal model and backfills into Markdown.

Use Task tool to dispatch `image-describer` sub-agent (config in `.opencode/agents/image-describer.md`):

```
Input:
- Image directory: output/mineru/images/ (already numbered by appearance order)
- Source Markdown: output/mineru/full_with_pages.md
- Output Markdown: output/mineru/full_with_pages_described.md
```

> **Serial batch constraint (hard rule):** Never dispatch multiple image-describer sub-agents concurrently. Complete one batch and save JSON before starting the next.

After this step, Step 2 uses `full_with_pages_described.md` instead of `full_with_pages.md`.

### 2. Analyze Courseware Structure

Read `full_with_pages_described.md` (or `full_with_pages.md`) and build a content map.

#### Traditional type

- Record core concepts, formulas, figures per page
- Identify logical chains: concept introduction → derivation → conclusion → application
- Mark dependencies between pages
- Flag exercise pages and experimental method pages

#### Slide-based type

Based on Step 0d-slide Topic Map, build detailed content map per Topic:
- Core content per page (formulas, algorithms, concepts, figures)
- Logical chains: problem/motivation → mechanism → application/significance
- Cross-Topic dependencies
- Mark core vs auxiliary slides per Topic

### 3. Write Lecture Notes (page-driven, strictly following courseware page order)

**Core principle: Notes content is organized strictly by original page order (P1→P2→P3→...).** Page ranges are embedded in section titles for cross-referencing.

**Language:** Follow courseware's original language. User can specify otherwise.

Based on `courseware_type`, use different templates:

---

#### Traditional Mode Template

**For:** Physics, Chemistry, Materials Science etc.

**Cognition path: Analogy → Derivation → Physical Meaning**

One Markdown file per chapter. See `references/writing-style-guide.md` for detailed examples.

```
# Section X Title

## 1. Overview
(2-3 sentences: what problem, why important, connection to previous section. Note page range)

## 2. Core Concepts & Derivation (page order)

### 2.1 [Page P1] Title
(Analogy → Derivation → Meaning)

## 3. Experimental Methods (if any, still page order)

## 4. Common Misconceptions
(Comparison table. Not tied to specific pages)

## 5. Exam Key Points
### Concepts | Calculations | Proofs | Analysis

## 6. Page Coverage Checklist
| ✅ | Page | Section | Core Content |
|---|------|---------|-------------|
| [ ] | P1 | ... | ... |
```

---

#### Slide-Based Mode Template

**For:** CS, AI, Engineering etc.

**Cognition path: Problem/Motivation → Core Mechanism → Application/Significance**

One Markdown file per Lecture. Based on Topic Map from Step 0d-slide.

```
# Lecture XX: Title (Pages P1-P74)

## 1. Overview

## 2. Topic 1 (Pages P5-P25)
### [Page P5] Why do we need...
### [Page P6-P8] Core mechanism...

## 3. Topic 2 (Pages P26-P40)

## 4. Common Misconceptions

## 5. Exam Key Points

## 6. Page Coverage Checklist
```

---

#### Page Annotation Rules (both modes)

1. **Title format**: `### N.M [Page PX] Title` (traditional) or `### [Page PX] Title` (slide-based)
2. **Strictly increasing**: All section page numbers must be monotonically increasing
3. **Merge consecutive pages**: `[Page P3-P4]` for same topic, max 3 pages merged (traditional) or relaxed (slide-based)
4. **Cross-reference exception**: Use `> **Note: See [Page P15] (Section 3.2) for details on XXX**` but do not expand here
5. **Every page must appear**: Coverage checklist must include all pages, including image-only pages
6. **Exercise pages**: Marked as independent subsections with reference answer frameworks
7. **Slide-based specific**: Topic (`##` level) maps to a continuous page range; pages within Topic are consecutive

### 4. Write Exam Summary

After all chapters, output a cross-chapter exam summary:
- **Formula cheat sheet** (formula + meaning + importance ★★★)
- **Concept questions** (standard answer frameworks)
- **Calculation questions** (typical steps and numerical examples)
- **Proof questions** (derivation approach and key steps)
- **Comprehensive analysis** (cross-chapter)
- **Pre-exam checklist** (checkbox format)

### 5. Sub-agent Review Iteration (per chapter)

> **Important: This is an iterative loop, not a single Review! Must re-Review after revisions until termination conditions are met.**

After each chapter, dispatch `lecture-reviewer` sub-agent (config in `.opencode/agents/lecture-reviewer.md`). Temperature=0.4, read-only (edit: deny, bash: deny).

**Review loop (must execute fully):**

```
round = 0
while True:
    round += 1
    ┌─ Sub-agent Review (dispatch lecture-reviewer via Task tool)
    │  Input: notes path + original courseware md path (full_with_pages.md)
    │  Output: 7-dimension scores + Critical/Major/Minor suggestions
    │
    ├─ Termination check:
    │  ✅ Score ≥ 8/10 and no Critical → exit
    │  ✅ round == 3 → exit
    │  ✅ No new insights for 2 consecutive rounds → exit
    │  ❌ None above → continue
    │
    ├─ Main agent evaluates each suggestion (adopt/reject with reason)
    │
    └─ Main agent revises notes (adopted suggestions applied immediately)
    → Return to loop start, re-Review revised notes
```

**7 evaluation dimensions:**

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Concept Clarity | 20% | Clear definitions and analogies for new concepts; terms explained on first occurrence |
| Derivation Coherence | 15% | Every derivation step traceable; no unexplained jumps |
| Logical Flow | 10% | Natural transitions between paragraphs/sections; no logical gaps |
| Analogy Appropriateness | 10% | Analogies close to everyday experience; no harder concepts introduced |
| Page Order Strictness | 10% | Section page numbers strictly increasing; checklist covers all pages |
| Self-Study Friendliness | 10% | Students can follow page-by-page; page annotations clear at a glance |
| Content Accuracy | 25% | Notes faithfully reflect original courseware; no misinterpretation or omissions |

### 6. Upload to Notion (optional)

**Ask user at runtime:** whether to upload to Notion.
- **No**: output "Workflow complete" and end.
- **Yes**: continue with pre-check and upload.

> **Prerequisite: All chapter Review iterations must be complete before uploading.**

For detailed Notion upload instructions, see [references/notion-upload.md](references/notion-upload.md).

**Key steps:**
1. Run pre-check: `python deps/notion/scripts/check_markdown_for_notion.py <file>`
2. Fix LaTeX pipe / table row issues
3. Upload via: `python deps/notion/scripts/archive_and_create_pages.py` + `add_markdown_to_page.py`

Notion page hierarchy is customizable. Ask user for their preferred structure (parent page name, course name, chapter names).

## Writing Principles

1. **Intuition before math**: Analogy first (traditional) or motivation first (slide-based)
2. **Traceable derivations**: Every step annotated with principle/approximation used
3. **LaTeX formulas**: Inline `$...$`, display `$$...$$`
4. **Bilingual terms**: First occurrence annotates opposite language (e.g. "Self-Attention (自注意力机制)")
5. **Comparison tables**: Side-by-side for easily confused concepts
6. **Exam points by type**: Concepts / Calculations / Proofs / Analysis
7. **Never pause mid-workflow**: Complete all chapters + exam summary + review before stopping
8. **Logical coherence**: Execute in chapter order; later chapters can reference earlier concepts
9. **Page-driven structure**: Strict P1→P2→P3 order
10. **Every page must appear**: Missing page in checklist = Critical defect
11. **Actionable review feedback**: Must reference specific paragraphs
12. **Language**: Follow courseware's original language; user can override
13. **Cognition path adaptation**: Traditional → analogy/derivation/meaning; Slide-based → problem/mechanism/application
14. **Topic clustering**: Slide-based notes auto-cluster by LLM-identified topic boundaries
15. **Maximize detail**: If logical relationships are not obvious from context, explain in detail. See `references/writing-style-guide.md`

## Dependencies

- **Notion skill**: Built-in at `deps/notion/`, requires `NOTION_API_KEY` in `.env`
- **MinerU skill**: Built-in at `deps/mineru/SKILL.md` (scripts use enhanced `scripts/mineru_extract.py`)
- **MinerU API**: Set `MINERU_TOKEN` in `.env` (from https://mineru.net/)
- **OCR tool**: `zai-mcp-server_extract_text_from_screenshot`
- **pdfplumber + pdf2image**: Page screenshots + fallback extraction (in `scripts/extract_pdf.py`)
- **pypdf**: PDF pre-splitting (in `scripts/split_pdf.py`)
- **requests**: MinerU API calls (in `scripts/mineru_extract.py`)

For MinerU API details, see [references/mineru-api-guide.md](references/mineru-api-guide.md).
For output file structure, see [references/output-structure.md](references/output-structure.md).

## Resources

### scripts/
- `split_pdf.py` — PDF analysis / pre-split / Markdown merge & split
- `extract_pdf.py` — Page screenshots + fallback text extraction
- `mineru_extract.py` — MinerU API PDF→Markdown conversion (VLM mode)
- `create_extraction_bat.py` — Generate .bat/.sh for extraction (cross-platform)
- `run_mineru_standalone.py` — Run MinerU extraction outside OpenCode
- `wait_for_extraction.py` — Poll for extraction completion
- `reconstruct_full_md.py` — Rebuild Markdown from content_list JSON
- `backfill_image_descriptions.py` — Backfill image descriptions into Markdown
- `save_batch_json.py` — Incrementally save image descriptions to JSON

### references/
- `writing-style-guide.md` — Writing style guide and templates
- `notion-upload.md` — Notion upload guide
- `mineru-api-guide.md` — MinerU API reference and pitfalls
- `output-structure.md` — Output file structure reference
