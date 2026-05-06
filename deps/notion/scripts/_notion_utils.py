#!/usr/bin/env python3
"""
Shared utilities for Notion API scripts.
Provides: API helpers, retry logic, proxy support, inline formatting.
"""

import requests
import re
import time
import sys
import os
import io
import subprocess

if sys.platform == 'win32':
    try:
        subprocess.run(['chcp', '65001'], shell=True,
                       capture_output=True, check=False)
    except Exception:
        pass
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

NOTION_KEY_FILE = os.path.expanduser("~/.config/notion/api_key")
NOTION_VERSION = '2025-09-03'

# Proxy configuration: reads from HTTPS_PROXY/HTTP_PROXY environment variables
# For China users: set these BEFORE running scripts:
#   Bash: export HTTPS_PROXY=http://127.0.0.1:10808
#   PowerShell: $env:HTTPS_PROXY="http://127.0.0.1:10808"
# If not set, scripts will attempt direct connection (may fail with ConnectionResetError)
PROXIES = {"https": os.environ.get("HTTPS_PROXY", ""),
           "http": os.environ.get("HTTP_PROXY", "")}
PROXIES = {k: v for k, v in PROXIES.items() if v}

MAX_RETRIES = 5
CHUNK_SIZE = 50
RETRY_DELAYS = [1, 2, 4, 8, 16]

LANG_MAP = {
    'python': 'python', 'py': 'python',
    'javascript': 'javascript', 'js': 'javascript',
    'typescript': 'typescript', 'ts': 'typescript',
    'bash': 'bash', 'shell': 'shell', 'sh': 'shell',
    'c++': 'c++', 'c#': 'c#', 'c': 'c',
    'java': 'java', 'go': 'go', 'rust': 'rust', 'sql': 'sql',
    'html': 'html', 'css': 'css', 'json': 'json',
    'yaml': 'yaml', 'yml': 'yaml', 'xml': 'xml',
    'markdown': 'markdown', 'md': 'markdown',
    'plain text': 'plain text', 'plaintext': 'plain text', 'text': 'plain text',
    'vue': 'vue', 'ruby': 'ruby', 'rb': 'ruby', 'php': 'php',
    'swift': 'swift', 'kotlin': 'kotlin', 'scala': 'scala', 'r': 'r',
    'matlab': 'matlab', 'lua': 'lua', 'perl': 'perl',
    'haskell': 'haskell', 'clojure': 'clojure', 'elixir': 'elixir',
    'erlang': 'erlang', 'f#': 'f#', 'fsharp': 'f#', 'ocaml': 'ocaml',
}


def get_api_key():
    with open(NOTION_KEY_FILE, 'r') as f:
        return f.read().strip()


def _request_with_retry(method, url, **kwargs):
    headers = kwargs.pop('headers', {})
    headers.setdefault('Authorization', 'Bearer ' + get_api_key())
    headers.setdefault('Notion-Version', NOTION_VERSION)
    kwargs['headers'] = headers
    for attempt in range(MAX_RETRIES):
        try:
            resp = getattr(requests, method)(
                url, proxies=PROXIES if PROXIES else None, timeout=30, **kwargs
            )
            if resp.status_code == 429:
                retry_after = int(resp.headers.get('Retry-After', 2))
                print(f"  Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            return resp
        except requests.exceptions.RequestException as e:
            print(f"  Network error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
    raise Exception(f"Failed after {MAX_RETRIES} retries: {url}")


def get_all_blocks(block_id):
    all_blocks = []
    cursor = None
    while True:
        url = f'https://api.notion.com/v1/blocks/{block_id}/children'
        params = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        resp = _request_with_retry('get', url, params=params)
        data = resp.json()
        all_blocks.extend(data.get('results', []))
        if data.get('has_more') and data.get('next_cursor'):
            cursor = data['next_cursor']
        else:
            break
    return all_blocks


def get_page_title(page_id):
    resp = _request_with_retry('get', f'https://api.notion.com/v1/pages/{page_id}')
    data = resp.json()
    props = data.get('properties', {})
    for prop in props.values():
        if prop.get('type') == 'title':
            title_parts = prop.get('title', [])
            return ''.join(t.get('plain_text', '') for t in title_parts)
    return page_id


def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:200] if name else 'untitled'


def append_blocks(page_id, blocks):
    url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    headers = {
        'Authorization': 'Bearer ' + get_api_key(),
        'Notion-Version': NOTION_VERSION,
        'Content-Type': 'application/json'
    }

    total_chunks = (len(blocks) + CHUNK_SIZE - 1) // CHUNK_SIZE
    failed_chunks = []

    for i in range(0, len(blocks), CHUNK_SIZE):
        chunk = blocks[i:i+CHUNK_SIZE]
        chunk_idx = i // CHUNK_SIZE
        success = False
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.patch(url, json={"children": chunk}, headers=headers,
                                      proxies=PROXIES if PROXIES else None, timeout=30)
                if resp.status_code == 200:
                    print(f"  Added {min(i+CHUNK_SIZE, len(blocks))}/{len(blocks)} blocks")
                    success = True
                    break
                elif resp.status_code == 429:
                    retry_after = int(resp.headers.get('Retry-After', 2))
                    print(f"  Rate limited, waiting {retry_after}s...")
                    time.sleep(retry_after)
                else:
                    print(f"  Error at {i} (attempt {attempt+1}): {resp.text[:200]}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAYS[attempt])
            except requests.exceptions.RequestException as e:
                print(f"  Network error at {i} (attempt {attempt+1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
        if not success:
            print(f"  FAILED chunk {chunk_idx} (blocks {i}-{min(i+CHUNK_SIZE-1, len(blocks)-1)}) after {MAX_RETRIES} retries")
            failed_chunks.append(chunk_idx)
        time.sleep(0.3)

    if failed_chunks:
        print(f"\n  WARNING: {len(failed_chunks)}/{total_chunks} chunks FAILED!")
        print(f"  Failed chunks: {failed_chunks}")
        print(f"  Page is INCOMPLETE. Consider archiving and re-uploading.")
    else:
        print(f"  All {total_chunks} chunks uploaded successfully.")


def parse_inline_formatting(text):
    """Parse markdown inline formatting into Notion rich_text with annotations.
    Supports: **bold**, *italic*, `code`, ~~strikethrough~~, [link](url), $inline math$.
    """
    if not text:
        return [_default_rich_text(text)]

    result = []
    parts = re.split(
        r'(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|~~[^~]+~~|\[[^\]]+\]\([^)]+\)|\$[^$]+\$)',
        text
    )

    for part in parts:
        if not part:
            continue

        if part.startswith('$') and part.endswith('$') and len(part) > 1:
            result.append({
                "type": "equation",
                "equation": {"expression": part[1:-1]}
            })
            continue

        rich_text = _default_rich_text(part)

        if part.startswith('`') and part.endswith('`') and len(part) > 1:
            rich_text["text"]["content"] = part[1:-1]
            rich_text["annotations"]["code"] = True
        elif part.startswith('**') and part.endswith('**') and len(part) > 2:
            rich_text["text"]["content"] = part[2:-2]
            rich_text["annotations"]["bold"] = True
        elif part.startswith('*') and part.endswith('*') and len(part) > 1:
            rich_text["text"]["content"] = part[1:-1]
            rich_text["annotations"]["italic"] = True
        elif part.startswith('~~') and part.endswith('~~') and len(part) > 2:
            rich_text["text"]["content"] = part[2:-2]
            rich_text["annotations"]["strikethrough"] = True
        elif part.startswith('[') and '](' in part:
            match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', part)
            if match:
                rich_text["text"]["content"] = match.group(1)
                rich_text["text"]["link"] = {"url": match.group(2)}

        result.append(rich_text)

    return result if result else [_default_rich_text(text)]


def rich_text_to_markdown(rich_text_array):
    """Convert Notion rich_text array to markdown string."""
    if not rich_text_array:
        return ''
    parts = []
    for rt in rich_text_array:
        text = rt.get('plain_text', '') or rt.get('text', {}).get('content', '')
        annotations = rt.get('annotations', {})
        text_obj = rt.get('text') or {}
        href = rt.get('href') or text_obj.get('link', {}).get('url') if text_obj.get('link') else None

        if annotations.get('code'):
            text = f'`{text}`'
        if annotations.get('bold'):
            text = f'**{text}**'
        if annotations.get('italic'):
            text = f'*{text}*'
        if annotations.get('strikethrough'):
            text = f'~~{text}~~'
        if href:
            text = f'[{text}]({href})'

        parts.append(text)
    return ''.join(parts)


def _default_rich_text(content):
    return {
        "type": "text",
        "text": {"content": content},
        "annotations": {
            "bold": False, "italic": False, "strikethrough": False,
            "underline": False, "code": False, "color": "default"
        }
    }
