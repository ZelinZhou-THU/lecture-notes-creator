"""Incrementally save image descriptions to JSON.

Usage:
    python save_batch_json.py <json_path> <img_key> <description> [more_key description...]

Examples:
    python save_batch_json.py descriptions.json "images/img_001.jpg" "A diagram showing..."
    python save_batch_json.py descriptions.json "images/img_002.jpg" "Desc 2" "images/img_003.jpg" "Desc 3"
"""
import json
import sys
import os


def load_or_create(json_path):
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    return {}


def save(json_path, data):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 4 or len(sys.argv) % 2 != 0:
        print("Usage: python save_batch_json.py <json_path> <key1> <desc1> [key2 desc2] ...")
        sys.exit(1)

    json_path = sys.argv[1]
    data = load_or_create(json_path)

    args = sys.argv[2:]
    for i in range(0, len(args), 2):
        key, desc = args[i], args[i + 1]
        data[key] = desc

    save(json_path, data)
    print(f"Saved {len(args) // 2} entries to {json_path} (total: {len(data)})")


if __name__ == "__main__":
    main()
