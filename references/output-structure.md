# Output File Structure

## MinerU Success

```
<output_dir>/
├── pre_split/                  ← Pre-split sub-PDFs (only if >200 pages)
│   ├── chunk_001.pdf
│   ├── chunk_002.pdf
│   └── manifest.json
├── sections/                   ← Physically split chapter MDs (long chapters)
│   ├── section_4.1_Title.md
│   ├── manifest.json
│   └── images/
├── Notes_X.X_ChapterTitle.md  ← One per chapter (with page annotations)
├── Notes_ChX_ExamSummary.md  ← Cross-chapter summary
└── mineru/                    ← MinerU output (core, on success)
    ├── full.md                ← Raw Markdown (no page numbers)
    ├── full_with_pages.md     ← With page annotations (MinerU raw output)
    ├── full_with_pages_described.md ← With image descriptions (after Step 1c)
    ├── content_list.json      ← Structured content blocks (with page source)
    ├── content_list_v2.json   ← Same, v2 format
    ├── images/                ← Extracted images (renamed img_001.jpg ~ img_NNN.jpg)
    └── layout.json            ← Layout analysis
```

## MinerU Failure (Fallback)

```
<output_dir>/
├── images/
│   └── page_NN.png            ← Page screenshots
├── summary.txt                ← Page statistics
└── text/
    └── page_NN.txt            ← Per-page text
```
