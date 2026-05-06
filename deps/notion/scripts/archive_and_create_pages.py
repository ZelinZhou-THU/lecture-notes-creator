#!/usr/bin/env python3
"""
Archive old Notion pages and create new ones.
Use this when you need to clear a page but don't want to delete blocks one by one.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _notion_utils import get_api_key, _request_with_retry


def archive_page(page_id):
    try:
        resp = _request_with_retry('patch',
            f'https://api.notion.com/v1/pages/{page_id}',
            headers={'Content-Type': 'application/json'},
            json={"archived": True}
        )
        return resp.status_code in [200, 204]
    except Exception:
        return False


def create_page(title, parent_id):
    try:
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
            return resp.json()['id']
        else:
            print(f"  Failed to create '{title}': {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"  Failed to create '{title}': {e}")
        return None


def archive_and_create(page_ids, titles, parent_id):
    print("Archiving old pages...")
    for pid in page_ids:
        success = archive_page(pid)
        print(f"  {'Archived' if success else 'Failed'}: {pid}")

    time.sleep(0.5)

    print("\nCreating new pages...")
    new_ids = []
    for title in titles:
        page_id = create_page(title, parent_id)
        if page_id:
            print(f"  Created: {title} -> {page_id}")
            new_ids.append(page_id)
        else:
            print(f"  Failed: {title}")
        time.sleep(0.3)

    return new_ids


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python archive_and_create_pages.py <parent_id> <old_ids_file> <titles_file>")
        print("  old_ids_file: text file with page IDs (one per line)")
        print("  titles_file: text file with new page titles (one per line)")
        print("\nExample:")
        print("  echo 'abc123\\ndef456' > old.txt")
        print("  echo 'New Page 1\\nNew Page 2' > titles.txt")
        print("  python archive_and_create_pages.py parent_id old.txt titles.txt")
        sys.exit(1)

    parent_id = sys.argv[1]
    old_ids_file = sys.argv[2]
    titles_file = sys.argv[3]

    with open(old_ids_file, 'r') as f:
        old_ids = [line.strip() for line in f if line.strip()]

    with open(titles_file, 'r') as f:
        titles = [line.strip() for line in f if line.strip()]

    if len(old_ids) != len(titles):
        print("Error: number of old IDs and titles must match!")
        sys.exit(1)

    get_api_key()
    new_ids = archive_and_create(old_ids, titles, parent_id)

    print(f"\nCreated {len(new_ids)} new pages:")
    for pid in new_ids:
        print(f"  {pid}")
