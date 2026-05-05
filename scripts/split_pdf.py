"""PDF splitting utilities for long courseware PDFs.

Four subcommands:

  analyze    — Show PDF info (page count, size, whether pre-split is needed)
  pre_split  — Split a large PDF into chunks (default 150 pages each)
  merge_md   — Merge multiple MinerU full.md outputs into one
  split_md   — Split a single Markdown file by section headings (JSON plan)

Usage:
    python split_pdf.py analyze "input.pdf"
    python split_pdf.py pre_split "input.pdf" --output ./pre_split --chunk-size 150
    python split_pdf.py merge_md ./out1/full.md ./out2/full.md --output ./merged/full.md
    python split_pdf.py split_md ./merged/full.md --plan plan.json --output ./sections
"""

import argparse
import json
import os
import re
import shutil
import sys

import pdfplumber
from pypdf import PdfReader, PdfWriter

SECTION_HEADER_RE = re.compile(r"(?m)^\s*(\d+\.\d+)\s+[\u4e00-\u9fffA-Za-z]")
HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$", re.MULTILINE)
MAX_MINERU_PAGES = 200
DEFAULT_CHUNK_SIZE = 150


def cmd_analyze(args):
    """Analyze a PDF and report basic info."""
    pdf_path = args.pdf_path
    if not os.path.isfile(pdf_path):
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)

    needs_split = total_pages > MAX_MINERU_PAGES

    print(f"PDF: {pdf_path}")
    print(f"Pages: {total_pages}")
    print(f"Size: {file_size_mb:.1f} MB")
    print(f"Needs pre-split: {'Yes' if needs_split else 'No'} (threshold: {MAX_MINERU_PAGES} pages)")
    if needs_split:
        n_chunks = (total_pages + args.chunk_size - 1) // args.chunk_size
        print(f"Suggested chunks: {n_chunks} (chunk size: {args.chunk_size} pages)")

    toc_sections = _detect_toc(pdf_path)
    if toc_sections:
        print(f"\nTOC detected ({len(toc_sections)} sections):")
        for sec in toc_sections:
            print(f"  {sec['title']} (body page ~{sec.get('body_page', '?')})")

    preview_pages = min(args.preview, total_pages)
    print(f"\n--- First {preview_pages} pages preview ---")
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(preview_pages):
            text = pdf.pages[i].extract_text() or ""
            lines = text.strip().split("\n")
            preview = " | ".join(lines[:3]) if lines else "(empty)"
            try:
                print(f"  P{i+1}: {preview}")
            except UnicodeEncodeError:
                print(f"  P{i+1}: {preview.encode('ascii', 'replace').decode('ascii')}")

    result = {
        "pdf_path": pdf_path,
        "total_pages": total_pages,
        "size_mb": round(file_size_mb, 1),
        "needs_pre_split": needs_split,
        "max_pages": MAX_MINERU_PAGES,
        "chunk_size": args.chunk_size,
    }
    if toc_sections:
        result["toc_sections"] = toc_sections

    return result


def _detect_toc(pdf_path):
    """Detect TOC page (page with multiple section headers) and find body pages."""
    sections = []
    page_matches = {}

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            matches = SECTION_HEADER_RE.findall(text)
            if matches:
                page_matches[i + 1] = matches

    if not page_matches:
        return sections

    sorted_pages = sorted(page_matches.keys())

    is_toc = len(page_matches.get(sorted_pages[0], [])) >= 2

    if is_toc:
        toc_page = sorted_pages[0]
        toc_matches = page_matches[toc_page]
        body_pages = sorted_pages[1:] if len(sorted_pages) > 1 else []

        for idx, header_num in enumerate(toc_matches):
            lines = _get_header_lines(pdf_path, toc_page, header_num)
            title = lines[0] if lines else header_num
            body_page = body_pages[idx] if idx < len(body_pages) else None
            sections.append({
                "number": header_num,
                "title": title.strip(),
                "body_page": body_page,
            })
    else:
        for pg in sorted_pages:
            matches = page_matches[pg]
            lines = _get_header_lines(pdf_path, pg, matches[0])
            title = lines[0] if lines else matches[0]
            sections.append({
                "number": matches[0],
                "title": title.strip(),
                "body_page": pg,
            })

    return sections


def _get_header_lines(pdf_path, page_num, header_number):
    """Get lines containing the section header on a specific page."""
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[page_num - 1].extract_text() or ""
    for line in text.split("\n"):
        if re.search(rf"^{re.escape(header_number)}\s+\S", line.strip()):
            return [line.strip()]
    return []


def cmd_pre_split(args):
    """Split a large PDF into page-count-based chunks."""
    pdf_path = args.pdf_path
    output_dir = args.output or os.path.splitext(os.path.basename(pdf_path))[0] + "_split"
    chunk_size = args.chunk_size

    os.makedirs(output_dir, exist_ok=True)

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    chunks = []

    for start in range(0, total_pages, chunk_size):
        end = min(start + chunk_size, total_pages)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])

        chunk_idx = start // chunk_size + 1
        chunk_name = f"chunk_{chunk_idx:03d}.pdf"
        chunk_path = os.path.join(output_dir, chunk_name)
        with open(chunk_path, "wb") as f:
            writer.write(f)

        chunks.append({
            "file": chunk_name,
            "pages": f"{start + 1}-{end}",
            "page_start": start + 1,
            "page_end": end,
        })
        print(f"  Created: {chunk_name} (pages {start + 1}-{end})")

    manifest_path = os.path.join(output_dir, "manifest.json")
    manifest = {
        "source": os.path.basename(pdf_path),
        "total_pages": total_pages,
        "chunk_size": chunk_size,
        "chunks": chunks,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\nPre-split complete: {len(chunks)} chunks in {output_dir}")
    print(f"Manifest: {manifest_path}")
    return manifest


def cmd_merge_md(args):
    """Merge multiple MinerU full.md outputs into a single Markdown file."""
    md_paths = args.inputs
    output_path = args.output

    if not md_paths:
        print("Error: no input files provided", file=sys.stderr)
        sys.exit(1)

    output_dir = os.path.dirname(output_path) or "."
    os.makedirs(output_dir, exist_ok=True)
    output_images = os.path.join(output_dir, "images")
    os.makedirs(output_images, exist_ok=True)

    merged_parts = []
    total_images = 0

    for md_path in md_paths:
        if not os.path.isfile(md_path):
            print(f"Warning: {md_path} not found, skipping", file=sys.stderr)
            continue

        md_dir = os.path.dirname(os.path.abspath(md_path))
        md_images = os.path.join(md_dir, "images")

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        if os.path.isdir(md_images):
            for fname in os.listdir(md_images):
                src = os.path.join(md_images, fname)
                dst = os.path.join(output_images, fname)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    total_images += 1

        merged_parts.append(content)

    merged = "\n\n---\n\n".join(merged_parts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(merged)

    print(f"Merged {len(merged_parts)} files into {output_path}")
    print(f"Total characters: {len(merged)}")
    print(f"Images copied: {total_images}")
    return output_path


def cmd_split_md(args):
    """Split a Markdown file by section headings according to a JSON plan."""
    md_path = args.md_path
    plan_path = args.plan
    output_dir = args.output or os.path.splitext(os.path.basename(md_path))[0] + "_sections"

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    if plan_path:
        with open(plan_path, "r", encoding="utf-8-sig") as f:
            plan = json.load(f)
    else:
        plan = _auto_detect_plan(content)

    if not plan.get("sections"):
        print("No sections to split. Use --plan or ensure Markdown has detectable headings.")
        return []

    os.makedirs(output_dir, exist_ok=True)
    md_dir = os.path.dirname(os.path.abspath(md_path))
    output_images = os.path.join(output_dir, "images")
    source_images = os.path.join(md_dir, "images")
    if os.path.isdir(source_images) and not os.path.isdir(output_images):
        shutil.copytree(source_images, output_images)

    lines = content.split("\n")
    sections = plan["sections"]
    created = []

    for idx, section in enumerate(sections):
        heading = section.get("heading", "")
        title = section.get("title", f"section_{idx + 1}")
        start_marker = section.get("start_marker", heading)
        is_first = (idx == 0)

        if not start_marker:
            if is_first:
                start_line = 0
            else:
                continue
        else:
            start_line = _find_heading_line(lines, start_marker)
            if start_line is None:
                print(f"  Warning: heading not found: {start_marker}")
                continue

        if idx + 1 < len(sections):
            next_section = sections[idx + 1]
            next_marker = next_section.get("start_marker") or next_section.get("heading", "")
            end_line = _find_heading_line(lines, next_marker) if next_marker else len(lines)
        else:
            end_line = len(lines)

        section_content = "\n".join(lines[start_line:end_line])
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
        filename = f"section_{safe_title}.md"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(section_content)

        page_count = end_line - start_line
        created.append({"file": filename, "title": title, "lines": page_count})
        print(f"  Created: {filename} ({page_count} lines)")

    manifest = {"source": os.path.basename(md_path), "sections": created}
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\nSplit complete: {len(created)} sections in {output_dir}")
    return created


def _auto_detect_plan(content):
    """Auto-detect section structure from Markdown headings."""
    sections = []
    for match in re.finditer(r"^(#{1,3})\s+(.*)$", content, re.MULTILINE):
        level = len(match.group(1))
        heading = match.group(2).strip()
        if level <= 2 and re.match(r"\d+\.\d+", heading):
            sections.append({
                "heading": heading,
                "start_marker": heading,
                "title": heading,
            })
    return {"sections": sections}


def _find_heading_line(lines, marker):
    """Find the line number where a heading marker appears.

    Only matches lines that start with '#' (Markdown headings),
    to avoid false positives from body text like '4.73' in tables.
    """
    marker_stripped = marker.lstrip("#").strip()
    for i, line in enumerate(lines):
        if not line.strip().startswith("#"):
            continue
        line_stripped = line.lstrip("#").strip()
        if line_stripped and line_stripped == marker_stripped:
            return i
        if line_stripped and line_stripped.startswith(marker_stripped):
            return i
    marker_lower = marker_stripped.lower()
    for i, line in enumerate(lines):
        if not line.strip().startswith("#"):
            continue
        line_stripped = line.lstrip("#").strip()
        if line_stripped and line_stripped.lower().startswith(marker_lower[:20]):
            return i
    return None


def main():
    parser = argparse.ArgumentParser(
        description="PDF splitting utilities for long courseware PDFs"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze PDF structure and info")
    p_analyze.add_argument("pdf_path", help="Path to PDF file")
    p_analyze.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE,
                           help=f"Chunk size for pre-split suggestion (default: {DEFAULT_CHUNK_SIZE})")
    p_analyze.add_argument("--preview", type=int, default=3,
                           help="Number of pages to preview (default: 3)")

    # pre_split
    p_split = subparsers.add_parser("pre_split", help="Split PDF into page-based chunks")
    p_split.add_argument("pdf_path", help="Path to PDF file")
    p_split.add_argument("--output", default=None, help="Output directory")
    p_split.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE,
                         help=f"Pages per chunk (default: {DEFAULT_CHUNK_SIZE})")

    # merge_md
    p_merge = subparsers.add_parser("merge_md", help="Merge multiple Markdown files")
    p_merge.add_argument("inputs", nargs="+", help="Paths to full.md files to merge")
    p_merge.add_argument("--output", required=True, help="Output merged Markdown path")

    # split_md
    p_splitmd = subparsers.add_parser("split_md", help="Split Markdown by section headings")
    p_splitmd.add_argument("md_path", help="Path to Markdown file")
    p_splitmd.add_argument("--plan", default=None,
                           help="JSON file with split plan (auto-detect if omitted)")
    p_splitmd.add_argument("--output", default=None, help="Output directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "pre_split":
        cmd_pre_split(args)
    elif args.command == "merge_md":
        cmd_merge_md(args)
    elif args.command == "split_md":
        cmd_split_md(args)


if __name__ == "__main__":
    main()
