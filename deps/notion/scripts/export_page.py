#!/usr/bin/env python3
"""
Export a Notion page (with sub-pages and databases) to local Markdown/CSV files.
Handles: headings, paragraphs, lists, code, tables, callouts, quotes,
         dividers, images, files, child pages, child databases, equations, toggles.
"""

import csv
import sys
import os
import re
import time
import argparse
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(__file__))
from _notion_utils import (
    get_api_key, _request_with_retry, get_all_blocks, get_page_title,
    sanitize_filename, rich_text_to_markdown
)


def download_file(url, save_path):
    from _notion_utils import PROXIES, MAX_RETRIES, RETRY_DELAYS
    for attempt in range(MAX_RETRIES):
        try:
            import requests
            resp = requests.get(
                url, proxies=PROXIES if PROXIES else None,
                timeout=60, stream=True
            )
            if resp.status_code == 200:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                return True
            else:
                print(f"  Download failed (status {resp.status_code}): {save_path}")
                return False
        except Exception as e:
            print(f"  Download error (attempt {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
    return False


def extract_filename_from_url(url):
    path = unquote(url.split('?')[0])
    name = os.path.basename(path)
    if not name or '.' not in name:
        name = 'file'
    return name


def block_to_markdown(block, assets_dir, indent=0):
    btype = block.get('type', '')
    prefix = '  ' * indent
    result_lines = []

    if btype.startswith('heading_'):
        level = int(btype.split('_')[1])
        hashes = '#' * level
        rt = block.get(btype, {}).get('rich_text', [])
        text = rich_text_to_markdown(rt)
        if text:
            result_lines.append(f'{prefix}{hashes} {text}')

    elif btype == 'paragraph':
        rt = block.get('paragraph', {}).get('rich_text', [])
        text = rich_text_to_markdown(rt)
        if text:
            result_lines.append(f'{prefix}{text}')

    elif btype == 'bulleted_list_item':
        rt = block.get('bulleted_list_item', {}).get('rich_text', [])
        text = rich_text_to_markdown(rt)
        result_lines.append(f'{prefix}- {text}')
        if block.get('has_children'):
            children = get_all_blocks(block['id'])
            for child in children:
                result_lines.extend(block_to_markdown(child, assets_dir, indent + 1))

    elif btype == 'numbered_list_item':
        rt = block.get('numbered_list_item', {}).get('rich_text', [])
        text = rich_text_to_markdown(rt)
        result_lines.append(f'{prefix}1. {text}')
        if block.get('has_children'):
            children = get_all_blocks(block['id'])
            for child in children:
                result_lines.extend(block_to_markdown(child, assets_dir, indent + 1))

    elif btype == 'code':
        code_data = block.get('code', {})
        lang = code_data.get('language', '')
        rt = code_data.get('rich_text', [])
        code_text = rich_text_to_markdown(rt)
        result_lines.append(f'{prefix}```{lang}')
        for line in code_text.split('\n'):
            result_lines.append(f'{prefix}{line}')
        result_lines.append(f'{prefix}```')

    elif btype == 'quote':
        rt = block.get('quote', {}).get('rich_text', [])
        text = rich_text_to_markdown(rt)
        for line in text.split('\n'):
            result_lines.append(f'{prefix}> {line}')

    elif btype == 'divider':
        result_lines.append(f'{prefix}---')

    elif btype == 'callout':
        callout = block.get('callout', {})
        rt = callout.get('rich_text', [])
        text = rich_text_to_markdown(rt)
        emoji = ''
        icon = callout.get('icon', {})
        if icon.get('type') == 'emoji':
            emoji = icon.get('emoji', '')
        if emoji and text:
            result_lines.append(f'{prefix}<aside>')
            result_lines.append(f'{prefix}{emoji} {text}')
            result_lines.append(f'{prefix}</aside>')
        elif text:
            result_lines.append(f'{prefix}<aside>')
            for line in text.split('\n'):
                result_lines.append(f'{prefix}{line}')
            result_lines.append(f'{prefix}</aside>')

    elif btype == 'table':
        table = block.get('table', {})
        table_width = table.get('table_width', 0)
        has_header = table.get('has_column_header', False)

        if block.get('has_children'):
            rows = get_all_blocks(block['id'])
        else:
            rows = []

        if rows:
            md_rows = []
            for row in rows:
                if row.get('type') == 'table_row':
                    cells = row.get('table_row', {}).get('cells', [])
                    md_cells = []
                    for cell in cells:
                        if isinstance(cell, list):
                            md_cells.append(rich_text_to_markdown(cell))
                        else:
                            md_cells.append(str(cell))
                    md_rows.append(md_cells)

            if md_rows:
                for ri, row in enumerate(md_rows):
                    padded = row + [''] * (table_width - len(row))
                    result_lines.append(f'{prefix}| {" | ".join(padded[:table_width])} |')
                    if ri == 0 and has_header:
                        result_lines.append(f'{prefix}|{" | ".join(["---"] * table_width)}|')

    elif btype in ('image', 'file', 'pdf', 'video'):
        file_data = block.get(btype, {})
        file_type = file_data.get('type', '')

        caption_rt = file_data.get('caption', [])
        caption = rich_text_to_markdown(caption_rt)

        url = ''
        if file_type == 'file':
            url = file_data.get('file', {}).get('url', '')
        elif file_type == 'external':
            url = file_data.get('external', {}).get('external', {}).get('url', '') or \
                  file_data.get('external', {}).get('url', '')

        if url and assets_dir:
            filename = extract_filename_from_url(url)
            if caption:
                base, ext = os.path.splitext(filename)
                if ext:
                    safe_name = sanitize_filename(caption) + ext
                else:
                    safe_name = sanitize_filename(caption)
                if safe_name:
                    filename = safe_name
            save_path = os.path.join(assets_dir, filename)
            counter = 1
            while os.path.exists(save_path):
                name_base, name_ext = os.path.splitext(filename)
                save_path = os.path.join(assets_dir, f'{name_base}_{counter}{name_ext}')
                counter += 1
            rel_path = os.path.join('assets', os.path.basename(save_path))
            print(f"  Downloading: {filename}")
            if download_file(url, save_path):
                if btype == 'image':
                    result_lines.append(f'{prefix}![{caption}]({rel_path})')
                else:
                    result_lines.append(f'{prefix}[{caption or filename}]({rel_path})')
            else:
                if btype == 'image':
                    result_lines.append(f'{prefix}![{caption}]({url})')
                else:
                    result_lines.append(f'{prefix}[{caption or filename}]({url})')
        elif url:
            if btype == 'image':
                result_lines.append(f'{prefix}![{caption}]({url})')
            else:
                result_lines.append(f'{prefix}[{caption or url}]({url})')

    elif btype == 'bookmark':
        bookmark = block.get('bookmark', {})
        url = bookmark.get('url', '')
        caption = bookmark.get('caption', [])
        caption_text = rich_text_to_markdown(caption)
        result_lines.append(f'{prefix}[{caption_text or url}]({url})')

    elif btype == 'embed':
        embed = block.get('embed', {})
        url = embed.get('url', '')
        result_lines.append(f'{prefix}[Embed]({url})')

    elif btype == 'equation':
        expr = block.get('equation', {}).get('expression', '')
        result_lines.append(f'{prefix}$$')
        for line in expr.split('\n'):
            result_lines.append(f'{prefix}{line}')
        result_lines.append(f'{prefix}$$')

    elif btype == 'toggle':
        rt = block.get('toggle', {}).get('rich_text', [])
        text = rich_text_to_markdown(rt)
        result_lines.append(f'{prefix}<details><summary>{text}</summary>')
        if block.get('has_children'):
            children = get_all_blocks(block['id'])
            for child in children:
                ctype = child.get('type', '')
                if ctype == 'child_page':
                    child_title = child.get('child_page', {}).get('title', 'untitled')
                    safe_child = sanitize_filename(child_title)
                    result_lines.append(f'{prefix}  ## 📄 {child_title}')
                    result_lines.append(f'{prefix}  [View sub-page: ./{safe_child}/index.md]')
                elif ctype == 'child_database':
                    db_title = child.get('child_database', {}).get('title', 'untitled')
                    result_lines.append(f'{prefix}  ## 📊 {db_title}')
                else:
                    result_lines.extend(block_to_markdown(child, assets_dir, indent + 1))
        result_lines.append(f'{prefix}</details>')

    elif btype == 'link_to_page':
        linked = block.get('link_to_page', {})
        linked_id = linked.get('page_id') or linked.get('database_id', '')
        if linked_id:
            result_lines.append(f'{prefix}[Linked page: {linked_id}]')

    elif btype == 'synced_block':
        if block.get('has_children'):
            children = get_all_blocks(block['id'])
            for child in children:
                result_lines.extend(block_to_markdown(child, assets_dir, indent))

    elif btype == 'column_list' or btype == 'column':
        if block.get('has_children'):
            children = get_all_blocks(block['id'])
            for child in children:
                result_lines.extend(block_to_markdown(child, assets_dir, indent))

    return result_lines


def query_data_source(data_source_id):
    all_results = []
    cursor = None
    while True:
        url = f'https://api.notion.com/v1/data_sources/{data_source_id}/query'
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        resp = _request_with_retry('post', url, json=body,
                                   headers={'Content-Type': 'application/json'})
        data = resp.json()
        all_results.extend(data.get('results', []))
        if data.get('has_more') and data.get('next_cursor'):
            cursor = data['next_cursor']
        else:
            break
    return all_results


def get_data_source_schema(data_source_id):
    resp = _request_with_retry('get',
                               f'https://api.notion.com/v1/data_sources/{data_source_id}')
    data = resp.json()
    return data.get('data_source', {}).get('properties', {})


def property_to_csv_value(prop):
    ptype = prop.get('type', '')
    if ptype == 'title':
        return ''.join(t.get('plain_text', '') for t in prop.get('title', []))
    elif ptype == 'rich_text':
        return ''.join(t.get('plain_text', '') for t in prop.get('rich_text', []))
    elif ptype == 'select':
        return (prop.get('select') or {}).get('name', '')
    elif ptype == 'multi_select':
        return ', '.join(s.get('name', '') for s in prop.get('multi_select', []))
    elif ptype == 'date':
        d = prop.get('date') or {}
        start = d.get('start', '')
        end = d.get('end', '')
        return f'{start} ~ {end}' if end else start
    elif ptype == 'checkbox':
        return str(prop.get('checkbox', False))
    elif ptype == 'number':
        return str(prop.get('number', ''))
    elif ptype == 'url':
        return prop.get('url', '')
    elif ptype == 'email':
        return prop.get('email', '')
    elif ptype == 'phone_number':
        return prop.get('phone_number', '')
    elif ptype == 'files':
        return ', '.join(f.get('name', '') for f in prop.get('files', []))
    elif ptype == 'relation':
        return ', '.join(r.get('id', '') for r in prop.get('relation', []))
    elif ptype == 'formula':
        return str(prop.get('formula', {}).get('string', '') or
                   prop.get('formula', {}).get('number', '') or
                   prop.get('formula', {}).get('boolean', '') or
                   prop.get('formula', {}).get('date', ''))
    elif ptype == 'rollup':
        items = prop.get('rollup', {}).get('array', [])
        return ', '.join(property_to_csv_value(item) for item in items)
    elif ptype == 'people':
        return ', '.join(
            p.get('name', '') or p.get('id', '')
            for p in prop.get('people', [])
        )
    elif ptype == 'status':
        return (prop.get('status') or {}).get('name', '')
    return ''


def export_data_source_csv(data_source_id, output_path):
    rows = query_data_source(data_source_id)
    if not rows:
        print(f"  No rows found in data source {data_source_id}")
        return False

    schema = get_data_source_schema(data_source_id)
    prop_names = list(schema.keys())
    if not prop_names:
        first_props = rows[0].get('properties', {})
        prop_names = list(first_props.keys())

    csv_rows = []
    for row in rows:
        props = row.get('properties', {})
        csv_row = {}
        for name in prop_names:
            csv_row[name] = property_to_csv_value(props.get(name, {}))
        csv_rows.append(csv_row)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=prop_names)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"  Exported {len(csv_rows)} rows to {output_path}")
    return True


def export_data_source_md_table(data_source_id):
    rows = query_data_source(data_source_id)
    if not rows:
        return ''

    schema = get_data_source_schema(data_source_id)
    prop_names = list(schema.keys())
    if not prop_names:
        first_props = rows[0].get('properties', {})
        prop_names = list(first_props.keys())

    lines = []
    lines.append('| ' + ' | '.join(prop_names) + ' |')
    lines.append('|' + '|'.join([' --- '] * len(prop_names)) + '|')

    for row in rows:
        props = row.get('properties', {})
        values = []
        for name in prop_names:
            val = property_to_csv_value(props.get(name, {}))
            val = val.replace('|', '\\|').replace('\n', ' ')
            values.append(val)
        lines.append('| ' + ' | '.join(values) + ' |')

    return '\n'.join(lines)


def collect_child_pages_and_databases(blocks):
    found = []
    for block in blocks:
        btype = block.get('type', '')
        if btype == 'child_page':
            title = block.get('child_page', {}).get('title', 'untitled')
            found.append(('child_page', block['id'], title))
        elif btype == 'child_database':
            title = block.get('child_database', {}).get('title', 'untitled')
            found.append(('child_database', block['id'], title))
        if block.get('has_children'):
            try:
                children = get_all_blocks(block['id'])
                found.extend(collect_child_pages_and_databases(children))
            except Exception:
                pass
    return found


def export_page(page_id, output_dir, args):
    title = get_page_title(page_id)
    safe_title = sanitize_filename(title)
    page_dir = os.path.join(output_dir, safe_title)
    os.makedirs(page_dir, exist_ok=True)

    assets_dir = os.path.join(page_dir, 'assets') if not args.no_assets else None

    print(f"Exporting: {title}")
    print(f"  Output: {page_dir}")

    blocks = get_all_blocks(page_id)
    print(f"  Found {len(blocks)} blocks")

    all_children = collect_child_pages_and_databases(blocks)
    child_page_exports = [(cid, ctitle) for ctype, cid, ctitle in all_children if ctype == 'child_page']
    child_db_exports = [(cid, ctitle) for ctype, cid, ctitle in all_children if ctype == 'child_database']

    md_lines = []

    for block in blocks:
        btype = block.get('type', '')

        if btype == 'child_page':
            child_title = block.get('child_page', {}).get('title', 'untitled')
            safe_child = sanitize_filename(child_title)
            md_lines.append(f'## 📄 {child_title}')
            md_lines.append(f'[View sub-page: ./{safe_child}/index.md]')
            md_lines.append('')

        elif btype == 'child_database':
            db_title = block.get('child_database', {}).get('title', 'untitled')
            safe_db = sanitize_filename(db_title)
            md_lines.append(f'## 📊 {db_title}')

            if not args.no_csv:
                csv_path = os.path.join(page_dir, f'{safe_db}.csv')
                try:
                    export_data_source_csv(block['id'], csv_path)
                    md_lines.append(f'[CSV export: ./{safe_db}.csv]')
                except Exception as e:
                    print(f"  CSV export failed: {e}")
                    md_lines.append(f'[CSV export failed]')

            if not args.no_md_table:
                try:
                    md_table = export_data_source_md_table(block['id'])
                    if md_table:
                        md_lines.append('')
                        md_lines.append(md_table)
                except Exception as e:
                    print(f"  Markdown table export failed: {e}")

            md_lines.append('')

        else:
            block_md = block_to_markdown(block, assets_dir)
            md_lines.extend(block_md)

    md_content = '\n'.join(md_lines)
    index_path = os.path.join(page_dir, 'index.md')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"  Written: {index_path} ({len(md_lines)} lines)")

    if not args.no_children:
        for child_id, child_title in child_page_exports:
            print(f"\n  Exporting child page: {child_title}")
            try:
                export_page(child_id, output_dir, args)
            except Exception as e:
                print(f"  Failed to export child '{child_title}': {e}")

    return page_dir


def main():
    parser = argparse.ArgumentParser(description='Export Notion page to local Markdown/CSV files')
    parser.add_argument('page_id', help='Notion page ID to export')
    parser.add_argument('--output', '-o', default='./notion_export',
                        help='Output directory (default: ./notion_export)')
    parser.add_argument('--no-csv', action='store_true',
                        help='Skip CSV export for databases')
    parser.add_argument('--no-md-table', action='store_true',
                        help='Skip markdown table for databases')
    parser.add_argument('--no-assets', action='store_true',
                        help='Do not download images/files, keep URLs')
    parser.add_argument('--no-children', action='store_true',
                        help='Do not recursively export sub-pages')

    args = parser.parse_args()

    get_api_key()

    page_id = args.page_id
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Notion Export Tool")
    print(f"  Page ID: {page_id}")
    print(f"  Output:  {output_dir}")
    print(f"  Options: csv={'off' if args.no_csv else 'on'}, "
          f"md_table={'off' if args.no_md_table else 'on'}, "
          f"assets={'off' if args.no_assets else 'on'}, "
          f"children={'off' if args.no_children else 'on'}")
    print()

    export_page(page_id, output_dir, args)
    print(f"\nDone! Exported to: {output_dir}")


if __name__ == "__main__":
    main()
