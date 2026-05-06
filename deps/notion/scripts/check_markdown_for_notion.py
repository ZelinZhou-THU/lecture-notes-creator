"""Check Markdown tables for Notion upload issues.

Detects:
1. Unescaped LaTeX pipe (|) in table cells that would break column parsing
2. Inconsistent cell counts across rows

Usage:
    python check_markdown_for_notion.py <markdown_file>

Exit codes:
    0 - No issues found
    1 - Issues found (printed to stdout)
"""
import re
import sys
import os

PROTECTED_PIPE = '\x00PIPE\x00'


def check_tables(markdown_file):
    with open(markdown_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    problems = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('|'):
            table_rows = []
            while i < len(lines) and lines[i].startswith('|'):
                raw_line = lines[i]
                safe_line = re.sub(r'\\\|', PROTECTED_PIPE, raw_line)
                cells_raw = [c.strip().replace(PROTECTED_PIPE, '|') for c in safe_line.strip('|').split('|')]
                is_separator = all(
                    re.match(r'^:?-+:?$', re.sub(re.escape(PROTECTED_PIPE), '', c))
                    for c in cells_raw if c
                )
                if not is_separator and any(c for c in cells_raw):
                    table_rows.append((i + 1, cells_raw))
                i += 1

            if table_rows:
                widths = [len(row[1]) for row in table_rows]
                if len(set(widths)) > 1:
                    first_line = table_rows[0][0]
                    problems.append(
                        f"Line {first_line}: Inconsistent cell counts {widths}"
                    )
                if len(table_rows) > 100:
                    problems.append(
                        f"Line {table_rows[0][0]}: Table has {len(table_rows)} rows (Notion limit: 100)"
                    )
                for line_num, row in table_rows:
                    for cell in row:
                        unescaped = re.findall(r'(?<!\\)\|', cell)
                        if unescaped and '\\|' not in cell:
                            preview = cell[:60] + ('...' if len(cell) > 60 else '')
                            problems.append(
                                f"Line {line_num}: Unescaped pipe in cell - {preview}"
                            )
        else:
            i += 1

    return problems


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_markdown_for_notion.py <markdown_file>")
        sys.exit(1)

    markdown_file = sys.argv[1]
    if not os.path.exists(markdown_file):
        print(f"File not found: {markdown_file}")
        sys.exit(1)

    problems = check_tables(markdown_file)

    if problems:
        print(f"Found {len(problems)} issue(s):")
        for p in problems:
            print(f"  - {p}")
        print("\nFix: Convert tables with LaTeX pipes to bullet lists, or split tables >100 rows into multiple tables.")
        sys.exit(1)
    else:
        print("OK: No table issues found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
