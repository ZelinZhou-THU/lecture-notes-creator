#!/usr/bin/env python3
"""
Generate a .bat file for MinerU extraction that users can double-click to run.

This script creates a Windows batch file that runs MinerU extraction outside of
OpenCode, avoiding memory leaks and connection issues that cause system crashes.

Usage:
    python create_extraction_bat.py <pdf_path> --output <output_dir> [--mode auto|pipeline|vlm]

Output:
    <output_dir>/run_extraction.bat  — Double-clickable batch file
"""

import argparse
import os
import sys

# Template for the .bat file
# Uses {{ and }} to escape Python's .format() curly braces
BAT_TEMPLATE = r"""@echo off
chcp 65001 >nul
title MinerU PDF Extraction Tool
color 0A

echo ============================================================
echo           MinerU PDF Extraction Tool
echo ============================================================
echo.
echo PDF File:   {pdf_path}
echo Output Dir: {output_dir}
echo Mode:       {mode}
echo.
echo ============================================================
echo.

REM Check Python environment
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please ensure Python is installed and added to PATH.
    echo.
    pause
    exit /b 1
)

REM Check PDF file
if not exist "{pdf_path}" (
    echo [ERROR] PDF file not found: {pdf_path}
    echo.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist "{project_root}\.env" (
    echo [WARNING] .env file not found at {project_root}\.env
    echo Please ensure MINERU_TOKEN is set in the .env file.
    echo.
)

REM Create output directory
if not exist "{output_dir}" mkdir "{output_dir}"

REM Run extraction
echo [1/1] Running MinerU extraction...
echo.
python "{script_dir}\mineru_extract.py" "{pdf_path}" --output "{output_dir}" --mode {mode}
set EXTRACT_STATUS=%ERRORLEVEL%
echo.

if %EXTRACT_STATUS% neq 0 (
    echo.
    echo [ERROR] Extraction failed! Please check the error messages above.
    echo.
    pause
    exit /b 1
)

REM Open output directory
echo Opening output directory...
explorer "{output_dir}"

echo.
echo ============================================================
echo Extraction completed! Please return to OpenCode to continue.
echo ============================================================
echo.
pause
"""


def find_project_root():
    """Find the project root directory (contains .env file)."""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):  # Max 10 levels up
        if os.path.exists(os.path.join(current, ".env")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    # Fallback: use script's parent's parent
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description="Generate a .bat file for MinerU extraction"
    )
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--output", required=True, help="Output directory for extraction results")
    parser.add_argument(
        "--mode", choices=["auto", "pipeline", "vlm"], default="auto",
        help="Extraction mode (default: auto)"
    )
    args = parser.parse_args()

    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Find project root (for .env file)
    project_root = find_project_root()

    # Resolve paths
    pdf_path = os.path.abspath(args.pdf_path)
    output_dir = os.path.abspath(args.output)

    # Generate .bat content
    bat_content = BAT_TEMPLATE.format(
        pdf_path=pdf_path,
        output_dir=output_dir,
        mode=args.mode,
        script_dir=script_dir,
        project_root=project_root,
    )

    # Write .bat file
    bat_path = os.path.join(output_dir, "run_extraction.bat")
    os.makedirs(output_dir, exist_ok=True)

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    print(f"Generated .bat file: {bat_path}")
    print(f"\nPlease double-click to run this file to start extraction.")


if __name__ == "__main__":
    main()
