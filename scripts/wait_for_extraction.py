#!/usr/bin/env python3
"""
Wait for MinerU extraction to complete by monitoring the status file.

Usage:
    python wait_for_extraction.py <output_dir> [--timeout 600] [--interval 5]

Exit codes:
    0 - Extraction completed successfully
    1 - Extraction failed
    2 - Timeout waiting for completion
"""

import argparse
import json
import os
import sys
import time


def read_status(output_dir):
    """Read extraction status from JSON file."""
    status_file = os.path.join(output_dir, "extraction_status.json")
    if not os.path.exists(status_file):
        return None
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def wait_for_completion(output_dir, timeout=600, interval=5):
    """
    Wait for extraction to complete.

    Args:
        output_dir: Output directory containing extraction_status.json
        timeout: Maximum wait time in seconds
        interval: Poll interval in seconds

    Returns:
        dict: Final status data

    Raises:
        TimeoutError: If extraction doesn't complete within timeout
        RuntimeError: If extraction failed
    """
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            raise TimeoutError(f"Extraction did not complete within {timeout}s")

        status = read_status(output_dir)
        if status is None:
            print(f"  Waiting for status file... ({elapsed:.0f}s)")
            time.sleep(interval)
            continue

        state = status.get("status", "unknown")

        if state == "completed":
            print(f"  Extraction completed! ({elapsed:.0f}s)")
            return status
        elif state == "failed":
            error = status.get("error", "Unknown error")
            raise RuntimeError(f"Extraction failed: {error}")
        else:
            pid = status.get("pid", "?")
            print(f"  Extraction running (PID: {pid})... ({elapsed:.0f}s)")
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(
        description="Wait for MinerU extraction to complete"
    )
    parser.add_argument("output_dir", help="Output directory containing extraction_status.json")
    parser.add_argument("--timeout", type=int, default=600, help="Maximum wait time (default: 600s)")
    parser.add_argument("--interval", type=int, default=5, help="Poll interval (default: 5s)")
    args = parser.parse_args()

    print(f"Waiting for extraction to complete...")
    print(f"  Output: {args.output_dir}")
    print(f"  Timeout: {args.timeout}s")

    try:
        status = wait_for_completion(args.output_dir, args.timeout, args.interval)
        print(f"\nExtraction completed successfully!")
        output_files = status.get("output_files", {})
        for name, path in output_files.items():
            if path:
                print(f"  {name}: {path}")
        sys.exit(0)
    except TimeoutError as e:
        print(f"\nTimeout: {e}", file=sys.stderr)
        sys.exit(2)
    except RuntimeError as e:
        print(f"\nFailed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
