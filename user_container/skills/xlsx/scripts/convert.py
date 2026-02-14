# /// script
# dependencies = ["openpyxl", "pandas"]
# ///
"""
Excel Format Converter

Convert between Excel and other tabular formats:
- CSV/TSV to XLSX
- XLSX to CSV/TSV
- Multi-sheet XLSX to multiple CSVs

Usage:
    uv run convert.py <input_file> <output_file> [options]

Examples:
    uv run convert.py data.csv output.xlsx
    uv run convert.py report.xlsx report.csv --sheet "Summary"
    uv run convert.py multi.xlsx output_dir/ --all-sheets
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook


def csv_to_xlsx(input_path: str, output_path: str, sheet_name: str = "Sheet1") -> dict:
    """Convert CSV/TSV to XLSX."""
    try:
        # Detect delimiter
        with open(input_path, 'r') as f:
            first_line = f.readline()
            delimiter = '\t' if '\t' in first_line else ','

        df = pd.read_csv(input_path, delimiter=delimiter)
        df.to_excel(output_path, sheet_name=sheet_name, index=False)

        return {
            "status": "success",
            "input": input_path,
            "output": output_path,
            "rows": len(df),
            "columns": len(df.columns)
        }
    except Exception as e:
        return {"error": str(e)}


def xlsx_to_csv(input_path: str, output_path: str, sheet_name: str = None, delimiter: str = ",") -> dict:
    """Convert XLSX sheet to CSV/TSV."""
    try:
        if sheet_name:
            df = pd.read_excel(input_path, sheet_name=sheet_name)
        else:
            df = pd.read_excel(input_path)  # First sheet

        df.to_csv(output_path, index=False, sep=delimiter)

        return {
            "status": "success",
            "input": input_path,
            "output": output_path,
            "sheet": sheet_name or "(first sheet)",
            "rows": len(df),
            "columns": len(df.columns)
        }
    except Exception as e:
        return {"error": str(e)}


def xlsx_to_multiple_csv(input_path: str, output_dir: str, delimiter: str = ",") -> dict:
    """Convert all sheets in XLSX to separate CSVs."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        xl = pd.ExcelFile(input_path)

        results = []
        for sheet_name in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sheet_name)
            # Sanitize sheet name for filename
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in sheet_name)
            output_path = os.path.join(output_dir, f"{safe_name}.csv")
            df.to_csv(output_path, index=False, sep=delimiter)
            results.append({
                "sheet": sheet_name,
                "file": output_path,
                "rows": len(df),
                "columns": len(df.columns)
            })

        return {
            "status": "success",
            "input": input_path,
            "output_dir": output_dir,
            "sheets_exported": len(results),
            "details": results
        }
    except Exception as e:
        return {"error": str(e)}


def multiple_csv_to_xlsx(input_files: list, output_path: str) -> dict:
    """Combine multiple CSVs into one XLSX with multiple sheets."""
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            results = []
            for i, csv_file in enumerate(input_files):
                # Detect delimiter
                with open(csv_file, 'r') as f:
                    first_line = f.readline()
                    delimiter = '\t' if '\t' in first_line else ','

                df = pd.read_csv(csv_file, delimiter=delimiter)
                # Use filename (without extension) as sheet name
                sheet_name = Path(csv_file).stem[:31]  # Excel sheet name limit
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                results.append({
                    "file": csv_file,
                    "sheet": sheet_name,
                    "rows": len(df),
                    "columns": len(df.columns)
                })

        return {
            "status": "success",
            "output": output_path,
            "sheets_created": len(results),
            "details": results
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    if len(sys.argv) < 3:
        print("Usage: uv run convert.py <input> <output> [options]")
        print()
        print("Convert between Excel and CSV/TSV formats.")
        print()
        print("Options:")
        print("  --sheet NAME     Specify sheet name for XLSX to CSV conversion")
        print("  --all-sheets     Export all sheets to separate CSVs (output must be directory)")
        print("  --tsv            Use tab delimiter for CSV output")
        print("  --combine        Combine multiple CSVs into one XLSX (input is comma-separated list)")
        print()
        print("Examples:")
        print("  uv run convert.py data.csv output.xlsx")
        print("  uv run convert.py report.xlsx report.csv --sheet Summary")
        print("  uv run convert.py multi.xlsx ./csvs/ --all-sheets")
        print("  uv run convert.py 'a.csv,b.csv,c.csv' combined.xlsx --combine")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    sheet_name = None
    all_sheets = "--all-sheets" in sys.argv
    use_tsv = "--tsv" in sys.argv
    combine = "--combine" in sys.argv
    delimiter = "\t" if use_tsv else ","

    # Parse --sheet option
    for i, arg in enumerate(sys.argv):
        if arg == "--sheet" and i + 1 < len(sys.argv):
            sheet_name = sys.argv[i + 1]

    # Determine conversion type
    input_ext = Path(input_path).suffix.lower()
    output_ext = Path(output_path).suffix.lower()

    if combine:
        # Multiple CSVs to XLSX
        input_files = input_path.split(",")
        result = multiple_csv_to_xlsx(input_files, output_path)
    elif input_ext in [".csv", ".tsv"] and output_ext in [".xlsx", ".xlsm"]:
        result = csv_to_xlsx(input_path, output_path)
    elif input_ext in [".xlsx", ".xlsm", ".xls"] and all_sheets:
        result = xlsx_to_multiple_csv(input_path, output_path, delimiter)
    elif input_ext in [".xlsx", ".xlsm", ".xls"] and output_ext in [".csv", ".tsv"]:
        result = xlsx_to_csv(input_path, output_path, sheet_name, delimiter)
    else:
        result = {"error": f"Unsupported conversion: {input_ext} -> {output_ext}"}

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
