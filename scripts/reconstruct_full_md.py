#!/usr/bin/env python3
"""
Reconstruct full.md with page number annotations from content_list_v2.json.

MinerU's full.md loses page number information. This script rebuilds a
full markdown with "> [课件 P{N}]" annotations before each content block,
enabling page-accurate lecture note writing.

Usage:
    python reconstruct_full_md.py <content_list_v2.json> [--output <output.md>]

    python reconstruct_full_md.py mineru/content_list_v2.json --output mineru/full_with_pages.md
"""

import argparse
import json
import os
import sys
from pathlib import Path


def extract_text_from_content(content):
    """Extract readable text from a block content dict (handles nested structures)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                item_type = item.get("type", "")
                item_content = item.get("content", "")
                if item_type == "text":
                    parts.append(str(item_content))
                elif item_type == "equation_inline":
                    parts.append(f"${item_content}$")
                elif item_type == "equation_block":
                    parts.append(f"$${item_content}$$")
                else:
                    sub = extract_text_from_content(item_content)
                    if sub:
                        parts.append(sub)
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    if isinstance(content, dict):
        # nested content - try common keys
        for key in ["text", "content", "paragraph_content", "title_content",
                    "list_items", "item_content"]:
            if key in content:
                val = content[key]
                if isinstance(val, list):
                    result = extract_text_from_content(val)
                    if result:
                        return result
                elif isinstance(val, str):
                    return val
        # fallback: just return str
        return str(content) if content else ""
    return str(content) if content else ""


def format_block(block, page_num, lines):
    """Append a formatted block to lines list. Returns nothing (mutates lines)."""
    block_type = block.get("type", "")
    content = block.get("content", {})

    if block_type == "title":
        level = content.get("level", 1)
        heading = "#" * level
        text = extract_text_from_content(content)
        if text.strip():
            lines.append(f"{heading} {text}")

    elif block_type == "paragraph":
        text = extract_text_from_content(content)
        if text.strip():
            lines.append(f"> [Page P{page_num}]")
            lines.append(text)

    elif block_type in ("equation_interline", "equation_inline"):
        math = content.get("math_content", "")
        if math.strip():
            lines.append(f"> [Page P{page_num}]")
            lines.append(f"$$\n{math}\n$$")

    elif block_type == "table":
        html = content.get("html", "")
        if html.strip():
            lines.append(f"> [Page P{page_num}]")
            lines.append(html)

    elif block_type == "image":
        img_path = content.get("image_path", "") or content.get("image_source", {}).get("path", "")
        if img_path:
            lines.append(f"> [Page P{page_num}]")
            # Normalize path to use forward slashes
            img_path = img_path.replace("\\", "/")
            lines.append(f"![]({img_path})")

    elif block_type == "list":
        list_type = content.get("list_type", "text_list")
        items = content.get("list_items", [])
        if items:
            lines.append(f"> [Page P{page_num}]")
            for item in items:
                item_content = item.get("item_content", [])
                item_type = item.get("item_type", "")
                if item_type == "text":
                    text = extract_text_from_content(item_content)
                    if text.strip():
                        lines.append(f"- {text}")
                elif item_type == "equation":
                    text = extract_text_from_content(item_content)
                    if text.strip():
                        lines.append(f"- $${text}$$")
                else:
                    text = extract_text_from_content(item_content)
                    if text.strip():
                        lines.append(f"- {text}")

    elif block_type in ("page_header", "page_footer", "page_number"):
        # Skip these - they are layout noise
        pass

    else:
        # Fallback for any unhandled types
        text = extract_text_from_content(content)
        if text.strip():
            lines.append(f"> [Page P{page_num}]")
            lines.append(text)


def reconstruct(content_list_path: str, output_path: str):
    """Main reconstruction logic."""
    print(f"Loading {content_list_path}...")
    with open(content_list_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected list, got {type(data).__name__}")

    total_pages = len(data)
    print(f"Processing {total_pages} pages...")

    all_lines = []
    for page_idx, blocks in enumerate(data):
        page_num = page_idx + 1  # P1 = page index 0
        if not isinstance(blocks, list):
            blocks = [blocks]

        for block in blocks:
            format_block(block, page_num, all_lines)

        # Add a blank line between pages for readability
        all_lines.append("")

    print(f"Writing {len(all_lines)} lines to {output_path}...")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines))

    print(f"Done. Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Reconstruct full.md with page number annotations."
    )
    parser.add_argument("content_list", help="Path to content_list_v2.json")
    parser.add_argument(
        "--output", "-o",
        help="Output path (default: <input_dir>/full_with_pages.md)"
    )
    args = parser.parse_args()

    content_list_path = Path(args.content_list)
    if not content_list_path.exists():
        print(f"Error: file not found: {content_list_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        output_path = str(content_list_path.parent / "full_with_pages.md")

    reconstruct(str(content_list_path), output_path)


if __name__ == "__main__":
    main()
