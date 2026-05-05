#!/usr/bin/env python3
"""
Run MinerU extraction as an independent detached process.

This script launches mineru_extract.py as a detached process that runs
outside of OpenCode's process tree, avoiding memory leaks and connection
issues that cause system crashes.

Usage:
    python run_mineru_standalone.py <pdf_path> --output ./output_dir [--mode auto|pipeline|vlm] [--debug]

The script will:
1. Launch mineru_extract.py as a detached process
2. Write a status file to <output_dir>/extraction_status.json
3. Exit immediately (OpenCode can then monitor the status file)

Status file format:
{
    "status": "running" | "completed" | "failed",
    "pid": <process_id>,
    "start_time": <timestamp>,
    "end_time": <timestamp> | null,
    "error": <error_message> | null,
    "output_files": {
        "full.md": <path>,
        "full_with_pages.md": <path>,
        "content_list_v2.json": <path>
    }
}
"""

import argparse
import json
import os
import subprocess
import sys
import time


def get_script_dir():
    """Get the directory containing this script."""
    return os.path.dirname(os.path.abspath(__file__))


def get_mineru_script():
    """Get the path to mineru_extract.py."""
    return os.path.join(get_script_dir(), "mineru_extract.py")


def write_status(output_dir, status, pid=None, error=None, output_files=None):
    """Write extraction status to JSON file."""
    status_file = os.path.join(output_dir, "extraction_status.json")
    status_data = {
        "status": status,
        "pid": pid,
        "start_time": time.time(),
        "end_time": time.time() if status in ("completed", "failed") else None,
        "error": error,
        "output_files": output_files or {}
    }
    os.makedirs(output_dir, exist_ok=True)
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2, ensure_ascii=False)


def launch_extraction(pdf_path, output_dir, mode="auto", language="auto", debug=False):
    """
    Launch MinerU extraction as a detached process.

    Args:
        pdf_path: Path to PDF file
        output_dir: Output directory for extraction results
        mode: Extraction mode (auto/pipeline/vlm)
        language: Document language (auto/ch/en)
        debug: Enable debug logging

    Returns:
        int: PID of the launched process
    """
    mineru_script = get_mineru_script()

    # Build command
    cmd = [
        sys.executable,  # Python interpreter
        mineru_script,
        pdf_path,
        "--output", output_dir,
        "--mode", mode,
        "--language", language,
    ]
    if debug:
        cmd.append("--debug")

    # Write initial status
    write_status(output_dir, "running")

    # Launch detached process
    if sys.platform == "win32":
        # Windows: CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        proc = subprocess.Popen(
            cmd,
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    else:
        # Unix: double-fork to detach
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )

    # Update status with PID
    write_status(output_dir, "running", pid=proc.pid)

    return proc.pid


def main():
    parser = argparse.ArgumentParser(
        description="Run MinerU extraction as an independent detached process"
    )
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument(
        "--mode", choices=["auto", "pipeline", "vlm"], default="auto",
        help="Extraction mode (default: auto)"
    )
    parser.add_argument(
        "--language", choices=["auto", "ch", "en"], default="auto",
        help="Document language (default: auto)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.output is None:
        base = os.path.splitext(os.path.basename(args.pdf_path))[0]
        args.output = base + "_mineru"

    print(f"Launching MinerU extraction as independent process...")
    print(f"  PDF: {args.pdf_path}")
    print(f"  Output: {args.output}")
    print(f"  Mode: {args.mode}")

    pid = launch_extraction(
        args.pdf_path, args.output, args.mode, args.language, args.debug
    )

    print(f"\nExtraction launched successfully!")
    print(f"  PID: {pid}")
    print(f"  Status file: {os.path.join(args.output, 'extraction_status.json')}")
    print(f"\nMonitor progress by reading the status file.")
    print(f"Or wait for completion with:")
    print(f"  python {os.path.join(get_script_dir(), 'wait_for_extraction.py')} {args.output}")


if __name__ == "__main__":
    main()
