#!/usr/bin/env python3
"""Convert DOCX to PDF with proper Unicode/Polish character support.
Usage: python docx_to_pdf.py input.docx output.pdf
"""
import sys
import os

def convert(input_path: str, output_path: str) -> None:
    import mammoth
    import weasyprint

    with open(input_path, "rb") as f:
        result = mammoth.convert_to_html(f)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: "DejaVu Sans", "Helvetica Neue", Arial, sans-serif;
         font-size: 11pt; margin: 2cm; line-height: 1.5; color: #000; }}
  h1,h2,h3 {{ font-weight: bold; margin: .8em 0 .3em; }}
  p {{ margin: .4em 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: .5em 0; }}
  td, th {{ border: 1px solid #ccc; padding: 4px 8px; }}
</style>
</head><body>{result.value}</body></html>"""

    weasyprint.HTML(string=html).write_pdf(output_path)
    print(f"Converted: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: docx_to_pdf.py input.docx output.pdf")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
