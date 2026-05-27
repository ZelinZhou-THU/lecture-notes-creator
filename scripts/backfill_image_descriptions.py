"""回填图片描述到 Markdown 文件。

Usage:
    python backfill_image_descriptions.py <input_md> <output_md> <descriptions_json_or_file>

Args:
    input_md: 原始 Markdown 文件路径（full_with_pages.md）
    output_md: 输出 Markdown 文件路径（full_with_pages_described.md）
    descriptions_json_or_file: 图片描述的 JSON 字符串，或 JSON 文件路径（以 .json 结尾）

Examples:
    # 直接传 JSON 字符串（适合短内容）
    python backfill_image_descriptions.py input.md output.md '{"images/xxx.jpg": "描述内容"}'

    # 从 JSON 文件读取（推荐，避免 PowerShell 引号问题）
    python backfill_image_descriptions.py input.md output_md descriptions.json
"""

import re
import json
import sys
import os

def build_described_md(input_md, output_md, descriptions):
    """回填图片描述到 Markdown 文件"""

    with open(input_md, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配 ![](images/xxx.jpg) 或 ![image](images/xxx.jpg) 格式
    pattern = r'!\[.*?\]\((images/[^)]+)\)'

    def replace(match):
        img_path = match.group(1)
        # 标准化：去掉开头的 ./ 或 /
        normalized = img_path.replace('./', '').lstrip('/')
        if normalized in descriptions:
            desc = descriptions[normalized]
            return f'> **Image content:**\n> {desc}\n> ![]({img_path})'
        else:
            # 保留原样
            return match.group(0)

    result = re.sub(pattern, replace, content, flags=re.IGNORECASE)

    with open(output_md, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"Done: {output_md}")
    # 统计
    matched = sum(1 for m in re.finditer(pattern, content, re.IGNORECASE))
    described = sum(1 for k in descriptions if k in content)
    print(f"  Matched images: {matched}, With descriptions: {described}")

def main():
    if len(sys.argv) != 4:
        print("Usage: python backfill_image_descriptions.py <input_md> <output_md> <descriptions_json_or_file>")
        print("  3rd arg: JSON string, single .json file, or comma-separated .json files")
        print("  Multi-file example: python backfill_image_descriptions.py in.md out.md batch1.json,batch2.json")
        sys.exit(1)

    input_md = sys.argv[1]
    output_md = sys.argv[2]
    descriptions_arg = sys.argv[3]

    descriptions = {}
    parts = [p.strip() for p in descriptions_arg.split(',')]

    for part in parts:
        if part.endswith('.json') and os.path.isfile(part):
            with open(part, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    print(f"Error: {part} must contain a JSON object (dict)")
                    sys.exit(1)
                descriptions.update(data)
        else:
            try:
                data = json.loads(part)
                if not isinstance(data, dict):
                    print("descriptions must be a JSON object (dict)")
                    sys.exit(1)
                descriptions.update(data)
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                sys.exit(1)

    if not descriptions:
        print("Warning: No descriptions loaded")

    if not os.path.exists(input_md):
        print(f"Input file not found: {input_md}")
        sys.exit(1)

    build_described_md(input_md, output_md, descriptions)

if __name__ == "__main__":
    main()