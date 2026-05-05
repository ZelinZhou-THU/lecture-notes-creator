# Lecture Notes Creator

Convert confusing academic courseware (PDF) into easy-to-understand self-study lecture notes (Markdown) for undergraduates, with AI review iterations and Notion sync.

## Core Features

- **MinerU API High-Quality Extraction**: Use MinerU v4 API (default VLM mode) to extract text, formulas, tables, and images from PDFs; formulas in LaTeX, tables in HTML, perfectly preserving courseware content
- **Page-Driven Structure**: Lecture notes strictly follow the courseware page order (P1→P2→P3→...), every page accounted for, enabling students to study page-by-page against the original
- **Two Courseware Types Self-Adaptive**:
  - **Traditional/Sectioned** (physics, chemistry, materials science, etc.): intuition analogy → mathematical derivation → physical meaning
  - **Slide-Based** (CS, AI, engineering, etc.): problem/motivation → core mechanism → application/significance
- **Sub-Agent AI Review Iterations**: After each chapter is written, a sub-agent reviews from an undergraduate self-study perspective with 6-dimension scoring + iterative optimization; proceeds only when standards are met
- **Notion Cloud Sync**: Lecture notes can be uploaded to Notion knowledge base, integrated with course learning pages

## Quick Start

### Prerequisites

- Python 3.10+
- MinerU API Key (from [mineru.net](https://mineru.net/))
- (Optional) Notion API Key

### Installation Steps

1. **Clone the project**
   ```bash
   git clone https://github.com/your-repo/lecture-notes-creator.git
   cd lecture-notes-creator
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Key**
   Create `.env` file in project root:
   ```env
   MINERU_TOKEN=your_mineru_api_key_here
   NOTION_API_KEY=your_notion_api_key_here  # Optional
   ```

4. **Verify installation**
   ```bash
   python scripts/mineru_extract.py --help
   ```

### Basic Usage

1. **Analyze PDF** (optional, only needed if >200 pages)
   ```bash
   python scripts/split_pdf.py analyze "path/to/courseware.pdf" --preview 3
   ```

2. **MinerU Extraction** (generates .bat file, user double-clicks to run)
   ```bash
   python scripts/create_extraction_bat.py "path/to/courseware.pdf" --output ./output_dir/mineru --mode auto
   ```

3. **Tell OpenCode "extraction done"**, OpenCode checks status and continues

4. **Sub-agent analyzes images** (optional, recommended if many images)
   - Use Task tool to dispatch `image-describer` sub-agent

5. **Analyze courseware structure**
   - Identify courseware type (traditional / slide-based)
   - Traditional type: organize by chapters
   - Slide-based type: LLM auto-clusters topics

6. **Write lecture notes**
   - Write strictly following page order
   - After each chapter, sub-agent review iteration

7. **Upload to Notion** (optional)
   ```bash
   python <notion_skill>/scripts/check_markdown_for_notion.py <markdown_file>
   # After fixing issues
   python <notion_skill>/scripts/add_markdown_to_page.py <page_id> "lecture_notes.md"
   ```

## Project Structure

```
lecture-notes-creator/
├── SKILL.md                     # Skill definition file
├── README.md                    # This file (Chinese)
├── README_EN.md                 # English version
├── LICENSE                      # MIT License
├── NOTICE                       # Credits and open source components
├── .gitignore                   # Git ignore rules
├── .env                         # API Key config (create manually)
├── .opencode/
│   └── agents/
│       ├── lecture-reviewer.md  # Sub-agent: lecture notes Review
│       └── image-describer.md   # Sub-agent: image understanding
├── docs/
│   ├── INSTALLATION.md          # Installation guide (zh/en bilingual)
│   └── QUICKSTART.md            # Quick start (zh/en bilingual)
├── scripts/
│   ├── split_pdf.py             # PDF analyze/pre-split/merge
│   ├── extract_pdf.py           # Page screenshots (fallback)
│   ├── mineru_extract.py        # MinerU API calls
│   ├── create_extraction_bat.py # Generate .bat file (double-click to run)
│   ├── reconstruct_full_md.py  # Rebuild Markdown from JSON
│   ├── backfill_image_descriptions.py  # Image description backfill
│   ├── save_batch_json.py       # Incremental save image descriptions JSON
│   └── wait_for_extraction.py   # Wait for MinerU completion
└── references/
    ├── writing-style-guide.md   # Lecture notes writing style guide
    └── review-prompt.md         # Review prompt template (backup)
```

## Credits

This project is built upon the following open source components:

- **MinerU**: High-fidelity PDF content extraction tool, Modified Apache License 2.0
  - Repo: https://github.com/opendatalab/MinerU
- **notion skill** (from OpenClaw): Notion API integration, MIT License
  - Repo: https://github.com/openclaw/openclaw/tree/main/skills/notion
- **MinerU skill** (from LobeHub): Skill encapsulation reference, MIT License
  - Repo: https://lobehub.com/zh/skills/openclaw-skills-mineru

## License

Apache License 2.0