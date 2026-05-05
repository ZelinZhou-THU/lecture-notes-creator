"""Extract text and page images from a PDF courseware file.

Usage:
    python extract_pdf.py <pdf_path> [--output DIR] [--dpi DPI]

Output:
    <output>/text/page_01.txt  — extracted text per page
    <output>/images/page_01.png — page screenshot per page
    <output>/summary.txt — page-by-page content summary
"""

import argparse
import os
import sys

import pdfplumber
from pdf2image import convert_from_path


def extract_text(pdf_path, output_dir):
    text_dir = os.path.join(output_dir, "text")
    os.makedirs(text_dir, exist_ok=True)

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        summary_lines = [f"Total pages: {total_pages}", ""]

        for i, page in enumerate(pdf.pages):
            text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            text_file = os.path.join(text_dir, f"page_{i+1:02d}.txt")
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(text)
            char_count = len(text.strip())
            img_count = len(page.images)
            summary_lines.append(f"Page {i+1}: {char_count} chars, {img_count} images")

        summary_file = os.path.join(output_dir, "summary.txt")
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("\n".join(summary_lines))

    return total_pages


def extract_images(pdf_path, output_dir, dpi=200):
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    pages = convert_from_path(pdf_path, dpi=dpi)
    for i, img in enumerate(pages):
        img_file = os.path.join(images_dir, f"page_{i+1:02d}.png")
        img.save(img_file)

    return len(pages)


def main():
    parser = argparse.ArgumentParser(description="Extract text and images from PDF")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--output", default=None, help="Output directory (default: <pdf_name>_extract)")
    parser.add_argument("--dpi", type=int, default=200, help="Image DPI (default: 200)")
    parser.add_argument("--text-only", action="store_true", help="Extract text only, skip images")
    args = parser.parse_args()

    if args.output is None:
        base = os.path.splitext(os.path.basename(args.pdf_path))[0]
        args.output = base + "_extract"

    os.makedirs(args.output, exist_ok=True)

    print(f"Extracting from: {args.pdf_path}")
    print(f"Output directory: {args.output}")

    total = extract_text(args.pdf_path, args.output)
    print(f"Text extracted: {total} pages")

    if not args.text_only:
        img_count = extract_images(args.pdf_path, args.output, args.dpi)
        print(f"Images extracted: {img_count} pages at {args.dpi} DPI")

    print("Done.")


if __name__ == "__main__":
    main()
