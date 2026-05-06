#!/usr/bin/env python3
"""
Add formatted markdown content to a Notion page.
Handles: bold, italic, inline code, code blocks, headings (H1-H6),
         dividers, callouts (from <aside>), tables, lists, quotes,
         images (![](url)), equations ($$...$$), strikethrough (~~text~~).
"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(__file__))
from _notion_utils import (
    get_api_key, parse_inline_formatting, append_blocks, get_all_blocks, LANG_MAP
)


def parse_markdown_to_blocks(markdown_content):
    blocks = []
    lines = markdown_content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        if re.match(r'^#{1}\s', line):
            blocks.append({"type": "heading_1", "heading_1": {"rich_text": parse_inline_formatting(line[2:])}})
        elif re.match(r'^#{2}\s', line):
            blocks.append({"type": "heading_2", "heading_2": {"rich_text": parse_inline_formatting(line[3:])}})
        elif re.match(r'^#{3}\s', line):
            blocks.append({"type": "heading_3", "heading_3": {"rich_text": parse_inline_formatting(line[4:])}})
        elif re.match(r'^#{4}\s', line):
            blocks.append({"type": "heading_4", "heading_4": {"rich_text": parse_inline_formatting(line[5:])}})
        elif re.match(r'^#{5}\s', line):
            blocks.append({"type": "heading_5", "heading_5": {"rich_text": parse_inline_formatting(line[6:])}})
        elif re.match(r'^#{6}\s', line):
            blocks.append({"type": "heading_6", "heading_6": {"rich_text": parse_inline_formatting(line[7:])}})
        elif line.strip() in ('---', '***', '___'):
            blocks.append({"type": "divider", "divider": {}})
        elif line.strip().startswith('<aside>'):
            aside_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().endswith('</aside>'):
                aside_lines.append(lines[i])
                i += 1
            if i < len(lines):
                last = lines[i].strip()
                end_content = last[:-7].strip() if last.endswith('</aside>') else last
                if end_content:
                    aside_lines.append(end_content)
            content = '\n'.join(aside_lines).strip()
            if content:
                blocks.append({
                    "type": "callout",
                    "callout": {
                        "rich_text": parse_inline_formatting(content),
                        "icon": {"type": "emoji", "emoji": "💡"},
                        "color": "yellow_background"
                    }
                })
            i += 1
            continue
        elif re.match(r'^!\[.*?\]\(', line.strip()):
            m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)', line.strip())
            if m:
                caption = m.group(1)
                url = m.group(2)
                image_block = {
                    "type": "image",
                    "image": {"type": "external", "external": {"url": url}}
                }
                if caption:
                    image_block["image"]["caption"] = [{"type": "text", "text": {"content": caption}}]
                blocks.append(image_block)
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": parse_inline_formatting(re.sub(r'^[-*]\s', '', line))}})
        elif re.match(r'^\d+\.\s', line):
            main_text = re.sub(r'^\d+\.\s', '', line)
            sub_text_parts = [main_text]
            children = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                nxt_stripped = nxt.strip()
                if nxt_stripped.startswith('- ') or nxt_stripped.startswith('* '):
                    sub_text_parts.append(re.sub(r'^[-*]\s', '', nxt_stripped))
                    j += 1
                elif re.match(r'^\s+```', nxt):
                    m = re.match(r'^\s+```(\w+)?', nxt)
                    lang = LANG_MAP.get(m.group(1), 'plain text') if m.group(1) else 'plain text'
                    code_lines = []
                    j += 1
                    while j < len(lines) and not re.match(r'^\s+```', lines[j]):
                        code_lines.append(lines[j].strip())
                        j += 1
                    if j < len(lines):
                        j += 1
                    code_content = '\n'.join(code_lines)
                    children.append({"type": "code", "code": {"rich_text": parse_inline_formatting(code_content), "language": lang}})
                elif nxt_stripped == '':
                    if j + 1 < len(lines):
                        peek = lines[j+1].strip()
                        if peek.startswith('- ') or peek.startswith('* ') or re.match(r'^\s+```', lines[j+1]):
                            j += 1
                            continue
                    break
                elif re.match(r'^\d+\.\s', nxt):
                    break
                else:
                    break
            block = {"type": "numbered_list_item", "numbered_list_item": {"rich_text": parse_inline_formatting('\n'.join(sub_text_parts))}}
            if children:
                block["numbered_list_item"]["children"] = children
            blocks.append(block)
            i = j
            continue
        elif re.match(r'^>\s', line):
            blocks.append({"type": "quote", "quote": {"rich_text": parse_inline_formatting(line[2:])}})
        elif re.match(r'^(\s*)```', line):
            m = re.match(r'^(\s*)```(\w+)?', line)
            indent = len(m.group(1))
            lang = LANG_MAP.get(m.group(2), 'plain text') if m.group(2) else 'plain text'
            code_lines = []
            i += 1
            while i < len(lines) and not re.match(r'^' + r'\s'*indent + r'```', lines[i]):
                code_lines.append(lines[i][indent:] if len(lines[i]) >= indent else lines[i])
                i += 1
            blocks.append({"type": "code", "code": {"rich_text": parse_inline_formatting('\n'.join(code_lines)), "language": lang}})
            i += 1
            continue
        elif line.startswith('|'):
            table_rows = []
            while i < len(lines) and lines[i].startswith('|'):
                raw_line = lines[i]
                PROTECTED_PIPE = '\x00PIPE\x00'
                safe_line = re.sub(r'\\\|', PROTECTED_PIPE, raw_line)
                cells_raw = [c.strip().replace(PROTECTED_PIPE, '\\|') for c in safe_line.strip('|').split('|')]
                is_separator = all(re.match(r'^:?-+:?$', re.sub(re.escape(PROTECTED_PIPE), '', c)) for c in cells_raw if c)
                if not is_separator and any(c for c in cells_raw):
                    row_cells = [parse_inline_formatting(cell) for cell in cells_raw]
                    table_rows.append(row_cells)
                i += 1
            if table_rows:
                table_width = len(table_rows[0]) if table_rows else 0
                if table_width > 0:
                    rows = []
                    for row in table_rows:
                        padded = row + [[] for _ in range(table_width - len(row))]
                        rows.append({"type": "table_row", "table_row": {"cells": padded}})
                    blocks.append({
                        "type": "table",
                        "table": {
                            "table_width": table_width,
                            "has_column_header": True,
                            "has_row_header": False,
                            "children": rows
                        }
                    })
            continue
        elif line.strip().startswith('$$'):
            expr_lines = []
            if line.strip() == '$$':
                i += 1
                while i < len(lines) and lines[i].strip() != '$$':
                    expr_lines.append(lines[i])
                    i += 1
            else:
                expr = line.strip()[2:]
                if expr.endswith('$$'):
                    expr_lines.append(expr[:-2])
                else:
                    expr_lines.append(expr)
                    i += 1
                    while i < len(lines) and not lines[i].strip().endswith('$$'):
                        expr_lines.append(lines[i])
                        i += 1
                    if i < len(lines):
                        last = lines[i].strip()
                        if last.endswith('$$') and last != '$$':
                            expr_lines.append(last[:-2])
            expression = '\n'.join(expr_lines).strip()
            if expression:
                blocks.append({"type": "equation", "equation": {"expression": expression}})
            i += 1
            continue
        elif line.strip() == '':
            pass
        else:
            if line.strip():
                blocks.append({"type": "paragraph", "paragraph": {"rich_text": parse_inline_formatting(line)}})
        i += 1

    return blocks


def add_markdown_to_page(page_id, markdown_file):
    print(f"Reading: {markdown_file}")
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = parse_markdown_to_blocks(content)
    print(f"  Parsed {len(blocks)} blocks, appending to page...")

    append_blocks(page_id, blocks)

    print(f"  Verifying upload...")
    all_blocks = get_all_blocks(page_id)
    actual = len(all_blocks)
    expected = len(blocks)
    if actual < expected:
        print(f"  WARNING: Expected {expected} blocks but page has {actual}. Upload may be incomplete!")
    else:
        print(f"  Verification OK: {actual} blocks on page.")

    print(f"  Done!")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python add_markdown_to_page.py <page_id> <markdown_file>")
        print("Example: python add_markdown_to_page.py 351cb209... 'path/to/guide.md'")
        sys.exit(1)

    page_id = sys.argv[1]
    markdown_file = sys.argv[2]
    get_api_key()

    # Proxy check for China users
    https_proxy = os.environ.get("HTTPS_PROXY", "")
    http_proxy = os.environ.get("HTTP_PROXY", "")
    if not https_proxy and not http_proxy:
        print("⚠️  WARNING: HTTPS_PROXY/HTTP_PROXY environment variables not set!")
        print("   For China users: connection may fail with ConnectionResetError.")
        print("   Set before running:")
        print("     Bash: export HTTPS_PROXY=http://127.0.0.1:10808")
        print("           export HTTP_PROXY=http://127.0.0.1:10808")
        print("     PowerShell: $env:HTTPS_PROXY=\"http://127.0.0.1:10808\"")
        print("                  $env:HTTP_PROXY=\"http://127.0.0.1:10808\"")
        print()

    add_markdown_to_page(page_id, markdown_file)
