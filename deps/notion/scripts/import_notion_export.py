#!/usr/bin/env python3
"""
Import a Notion export directory back into Notion with high fidelity.
Reads the output of export_page.py and recreates pages, toggles, callouts,
images, equations, nested lists, and child page hierarchy.

Usage:
    python import_notion_export.py <parent_page_id> <export_dir>
    python import_notion_export.py <parent_page_id> <export_dir> --no-upload
"""

import sys
import os
import re
import time
import mimetypes
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _notion_utils import (
    get_api_key, _request_with_retry, append_blocks,
    parse_inline_formatting, sanitize_filename, get_page_title, LANG_MAP
)


def create_page(title, parent_id):
    resp = _request_with_retry('post',
        'https://api.notion.com/v1/pages',
        headers={'Content-Type': 'application/json'},
        json={
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {"title": [{"text": {"content": title}}]}
            }
        }
    )
    if resp.status_code == 200:
        page_id = resp.json()['id']
        print(f"  Created page: {title} -> {page_id}")
        return page_id
    else:
        print(f"  Failed to create '{title}': {resp.text[:200]}")
        return None


def upload_file_to_notion(file_path):
    filename = os.path.basename(file_path)
    content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    resp = _request_with_retry('post',
        'https://api.notion.com/v1/file_uploads',
        headers={'Content-Type': 'application/json'},
        json={
            "mode": "single_part",
            "filename": filename,
            "content_type": content_type
        }
    )
    if resp.status_code != 200:
        print(f"  File upload create failed: {resp.text[:200]}")
        return None

    file_upload_id = resp.json()['id']

    with open(file_path, 'rb') as f:
        import requests
        from _notion_utils import PROXIES, MAX_RETRIES, RETRY_DELAYS
        for attempt in range(MAX_RETRIES):
            try:
                upload_resp = requests.post(
                    f'https://api.notion.com/v1/file_uploads/{file_upload_id}/send',
                    headers={
                        'Authorization': 'Bearer ' + get_api_key(),
                        'Notion-Version': '2025-09-03'
                    },
                    files={'file': (filename, f, content_type)},
                    proxies=PROXIES if PROXIES else None,
                    timeout=60
                )
                if upload_resp.status_code == 200:
                    print(f"  Uploaded: {filename}")
                    return {"type": "file_upload", "file_upload": {"id": file_upload_id}}
                else:
                    print(f"  File upload send failed (attempt {attempt+1}): {upload_resp.text[:200]}")
                    if attempt < MAX_RETRIES - 1:
                        f.seek(0)
                        time.sleep(RETRY_DELAYS[attempt])
            except Exception as e:
                print(f"  File upload error (attempt {attempt+1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    f.seek(0)
                    time.sleep(RETRY_DELAYS[attempt])

    return None


def extract_emoji(text):
    m = re.match(r'^([\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF\u2300-\u23FF\u2B50\u231A\u231B\u23E9-\u23F3\u23F8-\u23FA\u25AA-\u25FE\u2614-\u2615\u2648-\u2653\u267F\u2693\u26A1\u26AA-\u26AB\u26BD-\u26BE\u26C4-\u26C5\u26CE\u26D4\u26EA\u26F2-\u26F3\u26F5\u26FA\u26FD\u2702\u2705\u2708-\u270D\u270F])\s*(.*)', text, re.DOTALL)
    if m:
        return m.group(1), m.group(2)
    return None, text


def parse_exported_markdown(content, export_dir, args):
    """Parse exported markdown into Notion blocks with high fidelity."""
    blocks = []
    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip(' ')
        indent = len(line) - len(stripped)

        if re.match(r'^#{1}\s', stripped):
            blocks.append({"type": "heading_1", "heading_1": {"rich_text": parse_inline_formatting(stripped[2:])}})
        elif re.match(r'^#{2}\s', stripped):
            blocks.append({"type": "heading_2", "heading_2": {"rich_text": parse_inline_formatting(stripped[3:])}})
        elif re.match(r'^#{3}\s', stripped):
            blocks.append({"type": "heading_3", "heading_3": {"rich_text": parse_inline_formatting(stripped[4:])}})
        elif re.match(r'^#{4}\s', stripped):
            blocks.append({"type": "heading_4", "heading_4": {"rich_text": parse_inline_formatting(stripped[5:])}})
        elif re.match(r'^#{5}\s', stripped):
            blocks.append({"type": "heading_5", "heading_5": {"rich_text": parse_inline_formatting(stripped[6:])}})
        elif re.match(r'^#{6}\s', stripped):
            blocks.append({"type": "heading_6", "heading_6": {"rich_text": parse_inline_formatting(stripped[7:])}})

        elif stripped.startswith('<details><summary>') and '</summary>' in stripped:
            summary_end = stripped.index('</summary>')
            summary_text = stripped[18:summary_end]
            children_lines = []
            i += 1
            while i < len(lines) and not lines[i].lstrip(' ').startswith('</details>'):
                children_lines.append(lines[i])
                i += 1
            toggle_block = {
                "type": "toggle",
                "toggle": {
                    "rich_text": parse_inline_formatting(summary_text),
                    "children": parse_exported_markdown('\n'.join(children_lines), export_dir, args)
                }
            }
            blocks.append(toggle_block)

        elif stripped.startswith('<aside>'):
            aside_lines = []
            i += 1
            while i < len(lines) and not lines[i].lstrip(' ').strip().endswith('</aside>'):
                aside_lines.append(lines[i].lstrip(' '))
                i += 1
            if i < len(lines):
                last = lines[i].lstrip(' ').strip()
                end_content = last[:-7].strip() if last.endswith('</aside>') else last
                if end_content:
                    aside_lines.append(end_content)
            content_text = '\n'.join(aside_lines).strip()
            if content_text:
                emoji, body = extract_emoji(content_text)
                callout = {
                    "type": "callout",
                    "callout": {
                        "rich_text": parse_inline_formatting(body),
                        "icon": {"type": "emoji", "emoji": emoji or "💡"},
                        "color": "yellow_background"
                    }
                }
                blocks.append(callout)
            i += 1
            continue

        elif re.match(r'^!\[([^\]]*)\]\(([^)]+)\)', stripped):
            m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)', stripped)
            caption = m.group(1)
            url_or_path = m.group(2)
            image_block = None

            if not url_or_path.startswith('http') and not args.no_upload:
                local_path = os.path.normpath(os.path.join(export_dir, url_or_path))
                if os.path.exists(local_path):
                    file_ref = upload_file_to_notion(local_path)
                    if file_ref:
                        image_block = {"type": "image", "image": file_ref}
                        if caption:
                            image_block["image"]["caption"] = [
                                {"type": "text", "text": {"content": caption}}
                            ]

            if not image_block:
                final_url = url_or_path
                if not url_or_path.startswith('http'):
                    final_url = url_or_path
                image_block = {
                    "type": "image",
                    "image": {"type": "external", "external": {"url": final_url}}
                }
                if caption:
                    image_block["image"]["caption"] = [
                        {"type": "text", "text": {"content": caption}}
                    ]

            blocks.append(image_block)

        elif re.match(r'^\$\$', stripped):
            expr_lines = []
            if stripped == '$$':
                i += 1
                while i < len(lines) and lines[i].lstrip(' ').strip() != '$$':
                    expr_lines.append(lines[i].lstrip(' '))
                    i += 1
            else:
                expr = stripped[2:]
                if expr.endswith('$$'):
                    expr_lines.append(expr[:-2])
                else:
                    expr_lines.append(expr)
                    i += 1
                    while i < len(lines) and not lines[i].lstrip(' ').strip().endswith('$$'):
                        expr_lines.append(lines[i].lstrip(' '))
                        i += 1
                    if i < len(lines):
                        last = lines[i].lstrip(' ').strip()
                        if last.endswith('$$') and last != '$$':
                            expr_lines.append(last[:-2])
            expression = '\n'.join(expr_lines).strip()
            if expression:
                blocks.append({"type": "equation", "equation": {"expression": expression}})
            i += 1
            continue

        elif stripped in ('---', '***', '___'):
            blocks.append({"type": "divider", "divider": {}})

        elif re.match(r'^- ', stripped):
            item_text = re.sub(r'^- ', '', stripped)
            blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": parse_inline_formatting(item_text)}})

        elif re.match(r'^\d+\.\s', stripped):
            main_text = re.sub(r'^\d+\.\s', '', stripped)
            sub_text_parts = [main_text]
            children = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                nxt_stripped = nxt.lstrip(' ')
                if re.match(r'^- ', nxt_stripped) and len(nxt) - len(nxt_stripped) > 0:
                    sub_text_parts.append(re.sub(r'^- ', '', nxt_stripped))
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
                        peek = lines[j+1].lstrip(' ')
                        if re.match(r'^- ', peek) or re.match(r'^\s+```', lines[j+1]):
                            j += 1
                            continue
                    break
                elif re.match(r'^\d+\.\s', nxt_stripped) and len(nxt) - len(nxt_stripped) == 0:
                    break
                else:
                    break
            block = {"type": "numbered_list_item", "numbered_list_item": {"rich_text": parse_inline_formatting('\n'.join(sub_text_parts))}}
            if children:
                block["numbered_list_item"]["children"] = children
            blocks.append(block)
            i = j
            continue

        elif re.match(r'^>\s', stripped):
            quote_text = re.sub(r'^>\s', '', stripped)
            blocks.append({"type": "quote", "quote": {"rich_text": parse_inline_formatting(quote_text)}})

        elif re.match(r'^(\s*)```', line):
            m = re.match(r'^(\s*)```(\w+)?', line)
            indent_len = len(m.group(1))
            lang = LANG_MAP.get(m.group(2), 'plain text') if m.group(2) else 'plain text'
            code_lines = []
            i += 1
            while i < len(lines) and not re.match(r'^' + r'\s'*indent_len + r'```', lines[i]):
                code_lines.append(lines[i][indent_len:] if len(lines[i]) >= indent_len else lines[i])
                i += 1
            blocks.append({"type": "code", "code": {"rich_text": parse_inline_formatting('\n'.join(code_lines)), "language": lang}})
            i += 1
            continue

        elif stripped.startswith('|'):
            table_rows = []
            while i < len(lines) and lines[i].lstrip(' ').startswith('|'):
                raw = lines[i].lstrip(' ')
                cells_raw = [c.strip() for c in raw.strip('|').split('|')]
                is_separator = all(re.match(r'^:?-+:?$', c) for c in cells_raw if c)
                if not is_separator and any(c for c in cells_raw):
                    row_cells = [parse_inline_formatting(cell) for cell in cells_raw]
                    table_rows.append(row_cells)
                i += 1
            if table_rows:
                table_width = len(table_rows[0]) if table_rows else 0
                if table_width > 0:
                    blocks.append({
                        "type": "table",
                        "table": {
                            "table_width": table_width,
                            "has_column_header": True,
                            "has_row_header": False,
                            "children": [{"type": "table_row", "table_row": {"cells": row}} for row in table_rows]
                        }
                    })
            continue

        elif re.match(r'^\[Embed\]\(([^)]+)\)', stripped):
            m = re.match(r'^\[Embed\]\(([^)]+)\)', stripped)
            if m:
                blocks.append({"type": "embed", "embed": {"url": m.group(1)}})

        elif stripped.startswith('[View sub-page:'):
            pass

        elif stripped.startswith('[CSV export:') or stripped.startswith('[Linked page:'):
            pass

        elif stripped == '':
            pass

        else:
            if stripped:
                m_link = re.match(r'^\[([^\]]+)\]\(([^)]+)\)$', stripped)
                if m_link:
                    link_text = m_link.group(1)
                    link_url = m_link.group(2)
                    if link_url.startswith('http') and not link_text.startswith('View') and not link_text.startswith('CSV'):
                        blocks.append({"type": "bookmark", "bookmark": {"url": link_url, "caption": [{"type": "text", "text": {"content": link_text}}]}})
                    else:
                        blocks.append({"type": "paragraph", "paragraph": {"rich_text": parse_inline_formatting(stripped)}})
                else:
                    blocks.append({"type": "paragraph", "paragraph": {"rich_text": parse_inline_formatting(stripped)}})

        i += 1

    return blocks


def find_sub_dirs(export_dir):
    """Find sub-page directories in an export directory."""
    sub_dirs = []
    if not os.path.isdir(export_dir):
        return sub_dirs
    for entry in os.listdir(export_dir):
        entry_path = os.path.join(export_dir, entry)
        index_path = os.path.join(entry_path, 'index.md')
        if os.path.isdir(entry_path) and os.path.exists(index_path):
            sub_dirs.append((entry, entry_path, index_path))
    return sub_dirs


def import_page(parent_id, index_path, export_base_dir, args):
    """Import a single exported page (index.md) into Notion."""
    page_dir = os.path.dirname(index_path)
    dir_name = os.path.basename(page_dir)

    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()

    title_guess = None
    first_line = content.split('\n')[0] if content.strip() else ''
    m = re.match(r'^#\s+(.+)$', first_line)
    if m:
        title_guess = m.group(1).strip()
    if not title_guess:
        title_guess = dir_name

    page_id = create_page(title_guess, parent_id)
    if not page_id:
        return None

    blocks = parse_exported_markdown(content, page_dir, args)
    if blocks:
        print(f"  Uploading {len(blocks)} blocks...")
        append_blocks(page_id, blocks)

    if not args.no_children:
        sub_dirs = find_sub_dirs(page_dir)
        for sub_name, sub_path, sub_index in sub_dirs:
            print(f"\n  Importing sub-page: {sub_name}")
            import_page(page_id, sub_index, export_base_dir, args)

    return page_id


def main():
    parser = argparse.ArgumentParser(description='Import a Notion export directory back into Notion')
    parser.add_argument('parent_page_id', help='Parent Notion page ID to import under')
    parser.add_argument('export_dir', help='Export directory (output of export_page.py)')
    parser.add_argument('--no-upload', action='store_true',
                        help='Do not upload local files (use external URLs only)')
    parser.add_argument('--no-children', action='store_true',
                        help='Do not recursively import sub-pages')

    args = parser.parse_args()

    get_api_key()

    export_dir = os.path.abspath(args.export_dir)
    parent_id = args.parent_page_id

    top_dirs = []
    for entry in sorted(os.listdir(export_dir)):
        entry_path = os.path.join(export_dir, entry)
        index_path = os.path.join(entry_path, 'index.md')
        if os.path.isdir(entry_path) and os.path.exists(index_path):
            top_dirs.append((entry, entry_path, index_path))

    if not top_dirs:
        print(f"No exported pages found in {export_dir}")
        sys.exit(1)

    print(f"Notion Import Tool")
    print(f"  Parent: {parent_id}")
    print(f"  Export: {export_dir}")
    print(f"  Pages found: {len(top_dirs)}")
    print()

    for name, path, index in top_dirs:
        print(f"Importing: {name}")
        import_page(parent_id, index, export_dir, args)
        print()

    print("Done!")


if __name__ == "__main__":
    main()
