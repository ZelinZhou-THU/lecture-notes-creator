#!/usr/bin/env python3
"""
Verify Notion page content and formatting.
Check for blocks, annotations, and formatting types.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _notion_utils import get_api_key, get_all_blocks


def verify_page(page_id):
    blocks = get_all_blocks(page_id)

    stats = {
        "heading_1": 0, "heading_2": 0, "heading_3": 0,
        "heading_4": 0, "heading_5": 0, "heading_6": 0,
        "paragraph": 0, "bulleted_list_item": 0,
        "numbered_list_item": 0, "quote": 0,
        "code": 0, "divider": 0, "table": 0,
        "callout": 0, "toggle": 0, "image": 0,
        "equation": 0, "other": 0
    }

    bold_count = 0
    italic_count = 0
    inline_code_count = 0
    strikethrough_count = 0

    for b in blocks:
        btype = b['type']
        if btype in stats:
            stats[btype] += 1
        else:
            stats["other"] += 1

        if btype in ['paragraph', 'bulleted_list_item', 'numbered_list_item', 'quote']:
            for r in b.get(btype, {}).get('rich_text', []):
                ann = r.get('annotations', {})
                if ann.get('bold'):
                    bold_count += 1
                if ann.get('italic'):
                    italic_count += 1
                if ann.get('code'):
                    inline_code_count += 1
                if ann.get('strikethrough'):
                    strikethrough_count += 1

    print(f"Page: {page_id}")
    print(f"Total blocks: {len(blocks)}")
    print("\nBlock types:")
    for btype, count in stats.items():
        if count > 0:
            print(f"  {btype}: {count}")

    print(f"\nInline formatting:")
    print(f"  bold: {bold_count}")
    print(f"  italic: {italic_count}")
    print(f"  inline code: {inline_code_count}")
    print(f"  strikethrough: {strikethrough_count}")

    print("\nSample callouts (if any):")
    for b in blocks:
        if b['type'] == 'callout':
            content = ''.join([r['text']['content'] for r in b['callout'].get('rich_text', [])])
            icon = b['callout'].get('icon', {})
            emoji = icon.get('emoji', '?') if icon.get('type') == 'emoji' else 'no-icon'
            print(f"  [{emoji}] {content[:80]}...")
            break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_page.py <page_id>")
        sys.exit(1)

    page_id = sys.argv[1]
    get_api_key()
    verify_page(page_id)
