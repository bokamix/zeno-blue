---
name: xlsx
description: "Complete Excel spreadsheet toolkit: create financial models, budgets, reports with formulas and formatting. Read/analyze complex workbooks with multiple sheets. Convert between Excel/CSV/TSV. Use when working with .xlsx, .xlsm, .xls, .csv, .tsv files - data analysis, financial modeling, budget creation, report generation, or any spreadsheet task."
license: Proprietary. LICENSE.txt has complete terms
---

# Excel Spreadsheet Skill

Complete toolkit for creating, reading, editing, and analyzing Excel spreadsheets. Supports complex financial models, multi-sheet workbooks, advanced formulas, charts, and formatting.

## Quick Reference: Helper Scripts

Located in `scripts/` directory. Run with `uv run scripts/<script>.py`:

| Script | Purpose | Example |
|--------|---------|---------|
| `recalc.py` | Recalculate formulas, detect errors | `uv run scripts/recalc.py model.xlsx` |
| `analyze.py` | Analyze file structure, formulas | `uv run scripts/analyze.py data.xlsx --full` |
| `convert.py` | Convert formats (CSV↔XLSX) | `uv run scripts/convert.py data.csv output.xlsx` |
| `compare.py` | Compare two Excel files | `uv run scripts/compare.py v1.xlsx v2.xlsx` |

---

## Output Requirements

### Zero Formula Errors
Every Excel file MUST be delivered with ZERO formula errors (#REF!, #DIV/0!, #VALUE!, #N/A, #NAME?). Always run `recalc.py` and fix any errors before delivery.

### Preserve Existing Templates
When modifying files with established patterns:
- Study and EXACTLY match existing format, style, and conventions
- Never impose standardized formatting on files with established patterns
- Existing template conventions ALWAYS override these guidelines

---

## Financial Model Standards

### Color Coding (Industry Standard)
| Color | RGB | Use For |
|-------|-----|---------|
| **Blue text** | 0,0,255 | Hardcoded inputs, scenario variables |
| **Black text** | 0,0,0 | ALL formulas and calculations |
| **Green text** | 0,128,0 | Links from other sheets (same workbook) |
| **Red text** | 255,0,0 | External links to other files |
| **Yellow background** | 255,255,0 | Key assumptions needing attention |

### Number Formatting
| Type | Format | Example |
|------|--------|---------|
| Years | Text string | "2024" not "2,024" |
| Currency | $#,##0 | Always specify units in headers ("Revenue ($mm)") |
| Zeros | Dash | Use format "$#,##0;($#,##0);-" |
| Percentages | 0.0% | One decimal default |
| Multiples | 0.0x | For EV/EBITDA, P/E, etc. |
| Negatives | Parentheses | (123) not -123 |

### Formula Construction Rules
1. **No hardcoded values in formulas** - Use cell references
   - ✅ `=B5*(1+$B$6)`
   - ❌ `=B5*1.05`
2. **Place ALL assumptions in separate cells** (growth rates, margins, multiples)
3. **Document hardcoded values** with source comments:
   - "Source: Company 10-K, FY2024, Page 45"
   - "Source: Bloomberg Terminal, 8/15/2025, AAPL US Equity"

---

## Core Workflow

### 1. Choose Your Tool

| Task | Best Tool | Notes |
|------|-----------|-------|
| Data analysis, bulk operations | **pandas** | Fast, powerful, great for CSV |
| Formulas, formatting, charts | **openpyxl** | Full Excel feature support |
| Complex tables with styling | **openpyxl** | Conditional formatting, merging |
| Quick CSV/XLSX conversion | **scripts/convert.py** | Handles multi-sheet |

### 2. Create/Edit Workflow

```
Create/Edit file → Save → Recalculate → Verify → Fix errors → Deliver
```

**CRITICAL**: openpyxl saves formulas but NOT calculated values. You MUST run recalc.py before delivery.

```bash
# After saving your Excel file
uv run scripts/recalc.py output.xlsx

# Check output for errors
# If status is "errors_found", fix them and recalc again
```

---

## Reading Excel Files

### Quick Read with pandas
```python
import pandas as pd

# Single sheet (first by default)
df = pd.read_excel('file.xlsx')

# Specific sheet
df = pd.read_excel('file.xlsx', sheet_name='Summary')

# All sheets as dict
all_sheets = pd.read_excel('file.xlsx', sheet_name=None)
for name, df in all_sheets.items():
    print(f"Sheet: {name}, Rows: {len(df)}")

# Specific columns only (faster for large files)
df = pd.read_excel('file.xlsx', usecols=['A', 'B', 'E:G'])

# With data types
df = pd.read_excel('file.xlsx', dtype={'ID': str, 'Amount': float})
```

### Read with openpyxl (preserves formulas)
```python
from openpyxl import load_workbook

# Read formulas (as strings)
wb = load_workbook('file.xlsx')
ws = wb.active
print(ws['B10'].value)  # Shows "=SUM(B2:B9)"

# Read calculated values (WARNING: don't save this workbook!)
wb_values = load_workbook('file.xlsx', data_only=True)
ws_values = wb_values.active
print(ws_values['B10'].value)  # Shows 1234.56
```

### Inspect File Structure
```bash
# Quick overview
uv run scripts/analyze.py file.xlsx

# With all formula locations
uv run scripts/analyze.py file.xlsx --formulas

# Full details (validations, conditional formatting)
uv run scripts/analyze.py file.xlsx --full
```

---

## Creating Excel Files

### CRITICAL: Use Formulas, Not Hardcoded Values

**Always use Excel formulas.** This keeps spreadsheets dynamic and updateable.

```python
# ❌ WRONG - Hardcoding calculated values
total = df['Sales'].sum()
sheet['B10'] = total  # Hardcodes 5000

# ✅ CORRECT - Using Excel formulas
sheet['B10'] = '=SUM(B2:B9)'
```

### Basic Creation
```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = "Summary"

# Add headers
headers = ['Item', 'Q1', 'Q2', 'Q3', 'Q4', 'Total']
for col, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=header)
    cell.font = Font(bold=True)
    cell.fill = PatternFill('solid', fgColor='DDDDDD')

# Add data with formulas
data = [
    ['Revenue', 100, 120, 140, 160],
    ['Costs', 60, 70, 80, 90],
]
for row_idx, row_data in enumerate(data, 2):
    for col_idx, value in enumerate(row_data, 1):
        ws.cell(row=row_idx, column=col_idx, value=value)
    # Add Total formula
    ws.cell(row=row_idx, column=6, value=f'=SUM(B{row_idx}:E{row_idx})')

# Profit row with formulas
ws['A4'] = 'Profit'
for col in range(2, 7):
    col_letter = get_column_letter(col)
    ws.cell(row=4, column=col, value=f'={col_letter}2-{col_letter}3')

wb.save('report.xlsx')
```

### From pandas DataFrame
```python
import pandas as pd

df = pd.DataFrame({
    'Product': ['A', 'B', 'C'],
    'Sales': [100, 200, 150],
    'Cost': [60, 120, 80]
})

# Simple export
df.to_excel('data.xlsx', index=False, sheet_name='Data')

# Multiple sheets
with pd.ExcelWriter('report.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Data', index=False)
    df.describe().to_excel(writer, sheet_name='Statistics')
```

---

## Editing Existing Files

### Preserve Formulas When Editing
```python
from openpyxl import load_workbook

wb = load_workbook('existing.xlsx')  # NOT data_only=True!
ws = wb.active

# Modify specific cells
ws['A1'] = 'Updated Header'
ws['B5'] = 999  # Change input value

# Add new rows
ws.insert_rows(10)
ws['A10'] = 'New Row'

# Delete columns
ws.delete_cols(3)

# Copy formulas (they auto-adjust references)
ws['F2'] = ws['E2'].value  # Copies formula with adjusted refs

wb.save('modified.xlsx')
```

### Add New Sheet
```python
wb = load_workbook('existing.xlsx')

# Create new sheet
new_ws = wb.create_sheet('Analysis')
new_ws['A1'] = 'Analysis Results'

# Reference data from other sheets
new_ws['B1'] = "=Data!B10"  # Cross-sheet reference

wb.save('existing.xlsx')
```

---

## Advanced Formulas

### Common Excel Functions
```python
# Statistical
ws['A1'] = '=AVERAGE(B2:B100)'
ws['A2'] = '=MEDIAN(B2:B100)'
ws['A3'] = '=STDEV(B2:B100)'
ws['A4'] = '=COUNT(B2:B100)'
ws['A5'] = '=COUNTIF(B2:B100,">100")'

# Lookup
ws['A6'] = '=VLOOKUP(D1,A2:C100,3,FALSE)'
ws['A7'] = '=INDEX(B2:B100,MATCH(D1,A2:A100,0))'
ws['A8'] = '=XLOOKUP(D1,A2:A100,B2:B100,"Not Found")'

# Conditional
ws['A9'] = '=IF(B1>100,"High","Low")'
ws['A10'] = '=IFS(B1>100,"High",B1>50,"Medium",TRUE,"Low")'
ws['A11'] = '=SUMIF(A2:A100,"Product A",B2:B100)'
ws['A12'] = '=SUMIFS(C2:C100,A2:A100,"Product A",B2:B100,">100")'

# Date/Time
ws['A13'] = '=TODAY()'
ws['A14'] = '=EOMONTH(A1,0)'  # End of month
ws['A15'] = '=NETWORKDAYS(A1,B1)'  # Working days

# Financial
ws['A16'] = '=NPV(0.1,B2:B10)'
ws['A17'] = '=IRR(B2:B10)'
ws['A18'] = '=PMT(0.05/12,360,200000)'  # Mortgage payment

# Text
ws['A19'] = '=CONCATENATE(A1," - ",B1)'
ws['A20'] = '=TEXT(B1,"$#,##0.00")'
ws['A21'] = '=LEFT(A1,5)'
```

### Array Formulas (Dynamic Arrays in Excel 365)
```python
# These spill results automatically
ws['A1'] = '=UNIQUE(B2:B100)'
ws['A1'] = '=SORT(B2:D100,1,1)'  # Sort by first column, ascending
ws['A1'] = '=FILTER(A2:C100,B2:B100>100)'
ws['A1'] = '=SEQUENCE(10,5,1,1)'  # 10 rows, 5 cols, start 1, step 1
```

### Named Ranges
```python
from openpyxl.workbook.defined_name import DefinedName

wb = Workbook()
ws = wb.active

# Create named range
wb.defined_names.add(DefinedName('SalesData', attr_text='Sheet!$B$2:$B$100'))
wb.defined_names.add(DefinedName('TaxRate', attr_text='Sheet!$E$1'))

# Use in formulas
ws['F1'] = '=SUM(SalesData)'
ws['F2'] = '=B10*TaxRate'
```

---

## Formatting

### Cell Styles
```python
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers

# Font
cell.font = Font(
    name='Arial',
    size=11,
    bold=True,
    italic=False,
    color='0000FF'  # Blue for inputs
)

# Fill
cell.fill = PatternFill(
    fill_type='solid',
    fgColor='FFFF00'  # Yellow
)

# Alignment
cell.alignment = Alignment(
    horizontal='center',
    vertical='center',
    wrap_text=True
)

# Border
thin_border = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)
cell.border = thin_border

# Number format
cell.number_format = '$#,##0.00'
cell.number_format = '0.0%'
cell.number_format = '#,##0;(#,##0);"-"'  # Negative in parens, zero as dash
cell.number_format = '0.0x'  # For multiples
```

### Column/Row Sizing
```python
# Column width
ws.column_dimensions['A'].width = 20
ws.column_dimensions['B'].width = 15

# Auto-fit (approximate)
for col in ws.columns:
    max_length = max(len(str(cell.value or '')) for cell in col)
    ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

# Row height
ws.row_dimensions[1].height = 30

# Freeze panes
ws.freeze_panes = 'B2'  # Freeze row 1 and column A
```

### Conditional Formatting
```python
from openpyxl.formatting.rule import (
    ColorScaleRule, FormulaRule, CellIsRule, DataBarRule
)
from openpyxl.styles import PatternFill

# Color scale (heat map)
ws.conditional_formatting.add('B2:B100',
    ColorScaleRule(
        start_type='min', start_color='FF0000',
        mid_type='percentile', mid_value=50, mid_color='FFFF00',
        end_type='max', end_color='00FF00'
    )
)

# Data bars
ws.conditional_formatting.add('C2:C100',
    DataBarRule(start_type='min', end_type='max', color='638EC6')
)

# Highlight cells
red_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
ws.conditional_formatting.add('D2:D100',
    CellIsRule(operator='lessThan', formula=['0'], fill=red_fill)
)

# Formula-based rule
ws.conditional_formatting.add('A2:E100',
    FormulaRule(formula=['$F2="Error"'], fill=red_fill)
)
```

### Data Validation (Dropdowns)
```python
from openpyxl.worksheet.datavalidation import DataValidation

# Dropdown list
dv = DataValidation(
    type="list",
    formula1='"Option A,Option B,Option C"',
    allow_blank=True
)
dv.prompt = "Select an option"
dv.promptTitle = "Category"
ws.add_data_validation(dv)
dv.add('B2:B100')

# Range-based dropdown
dv_range = DataValidation(type="list", formula1='=Categories!$A$2:$A$50')
ws.add_data_validation(dv_range)
dv_range.add('C2:C100')

# Number validation
dv_num = DataValidation(type="decimal", operator="between", formula1=0, formula2=100)
dv_num.error = "Value must be between 0 and 100"
ws.add_data_validation(dv_num)
dv_num.add('D2:D100')
```

---

## Charts

### Basic Column Chart
```python
from openpyxl.chart import BarChart, Reference

# Create chart
chart = BarChart()
chart.type = "col"  # Column chart
chart.title = "Sales by Quarter"
chart.y_axis.title = "Revenue ($)"
chart.x_axis.title = "Quarter"

# Data references (assuming data in A1:E3)
data = Reference(ws, min_col=2, min_row=1, max_col=5, max_row=3)
cats = Reference(ws, min_col=1, min_row=2, max_row=3)

chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)
chart.shape = 4  # Chart style

# Add to sheet
ws.add_chart(chart, "G2")
```

### Line Chart
```python
from openpyxl.chart import LineChart, Reference

chart = LineChart()
chart.title = "Trend Analysis"
chart.style = 10

data = Reference(ws, min_col=2, min_row=1, max_col=13, max_row=4)
chart.add_data(data, titles_from_data=True)

cats = Reference(ws, min_col=1, min_row=2, max_row=4)
chart.set_categories(cats)

# Customize
chart.y_axis.scaling.min = 0
chart.y_axis.scaling.max = 1000

ws.add_chart(chart, "G10")
```

### Pie Chart
```python
from openpyxl.chart import PieChart, Reference

chart = PieChart()
chart.title = "Market Share"

labels = Reference(ws, min_col=1, min_row=2, max_row=5)
data = Reference(ws, min_col=2, min_row=1, max_row=5)
chart.add_data(data, titles_from_data=True)
chart.set_categories(labels)

ws.add_chart(chart, "G2")
```

---

## Multi-Sheet Operations

### Cross-Sheet References
```python
# Reference another sheet
ws['A1'] = "=Summary!B10"
ws['A2'] = "='Q1 Data'!C5"  # Quote sheet names with spaces
ws['A3'] = "=SUM(Jan!B:B,Feb!B:B,Mar!B:B)"  # Sum across sheets

# 3D reference (same cell across multiple sheets)
ws['A4'] = "=SUM(Jan:Dec!B10)"  # Sum B10 from sheets Jan through Dec
```

### Copy Between Sheets
```python
from openpyxl import load_workbook
from copy import copy

wb = load_workbook('source.xlsx')
source_ws = wb['Template']

# Create new sheet from template
target_ws = wb.copy_worksheet(source_ws)
target_ws.title = 'Q1 Report'

# Or copy specific range
for row in source_ws['A1:E10']:
    for cell in row:
        target_ws[cell.coordinate].value = cell.value
        if cell.has_style:
            target_ws[cell.coordinate].font = copy(cell.font)
            target_ws[cell.coordinate].fill = copy(cell.fill)
```

### Consolidate Data from Multiple Sheets
```python
import pandas as pd

# Read all sheets
xl = pd.ExcelFile('multi_sheet.xlsx')
all_data = []
for sheet in xl.sheet_names:
    df = pd.read_excel(xl, sheet_name=sheet)
    df['Source_Sheet'] = sheet
    all_data.append(df)

# Combine
combined = pd.concat(all_data, ignore_index=True)
combined.to_excel('consolidated.xlsx', index=False)
```

---

## CSV/TSV Operations

### Read CSV
```python
import pandas as pd

# Auto-detect delimiter
df = pd.read_csv('data.csv')

# Explicit TSV
df = pd.read_csv('data.tsv', delimiter='\t')

# Handle encoding issues
df = pd.read_csv('data.csv', encoding='utf-8-sig')  # Remove BOM
df = pd.read_csv('data.csv', encoding='latin-1')

# Large files - chunked reading
for chunk in pd.read_csv('huge.csv', chunksize=10000):
    process(chunk)
```

### Convert Formats
```bash
# CSV to XLSX
uv run scripts/convert.py data.csv output.xlsx

# XLSX to CSV (first sheet)
uv run scripts/convert.py report.xlsx report.csv

# XLSX to CSV (specific sheet)
uv run scripts/convert.py report.xlsx summary.csv --sheet "Summary"

# All sheets to separate CSVs
uv run scripts/convert.py multi.xlsx ./csv_output/ --all-sheets

# Multiple CSVs to single XLSX (each CSV = one sheet)
uv run scripts/convert.py 'jan.csv,feb.csv,mar.csv' quarterly.xlsx --combine
```

---

## Formula Recalculation

openpyxl saves formulas but NOT calculated values. LibreOffice is used to recalculate.

### Recalculate and Verify
```bash
# Basic recalculation
uv run scripts/recalc.py model.xlsx

# With longer timeout (for complex models)
uv run scripts/recalc.py complex_model.xlsx 120
```

### Output Interpretation
```json
{
  "status": "success",
  "file": "model.xlsx",
  "total_errors": 0,
  "total_formulas": 156
}
```

If errors found:
```json
{
  "status": "errors_found",
  "total_errors": 3,
  "total_formulas": 156,
  "error_summary": {
    "#REF!": {
      "count": 2,
      "locations": ["Sheet1!B5", "Sheet1!C10"]
    },
    "#DIV/0!": {
      "count": 1,
      "locations": ["Summary!E15"]
    }
  }
}
```

### Fixing Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| #REF! | Invalid cell reference | Check if referenced cells exist, weren't deleted |
| #DIV/0! | Division by zero | Add `=IF(B1=0,0,A1/B1)` check |
| #VALUE! | Wrong data type | Ensure numbers aren't stored as text |
| #NAME? | Unknown function/range | Check spelling, define missing named ranges |
| #N/A | Lookup failed | Add `=IFERROR(VLOOKUP(...),0)` wrapper |
| #NUM! | Invalid numeric value | Check for negative roots, invalid IRR, etc. |

---

## Comparing Excel Files

```bash
# Compare two versions
uv run scripts/compare.py v1.xlsx v2.xlsx

# Compare specific sheet
uv run scripts/compare.py old.xlsx new.xlsx --sheet "Summary"

# Compare calculated values (not formulas)
uv run scripts/compare.py expected.xlsx actual.xlsx --values

# Summary only
uv run scripts/compare.py v1.xlsx v2.xlsx --summary
```

---

## Code Style Guidelines

**Python code** for Excel operations:
- Minimal, concise code without unnecessary comments
- Avoid verbose variable names
- Avoid unnecessary print statements

**Excel files themselves**:
- Add comments to cells with complex formulas
- Document data sources for hardcoded values
- Include notes for key calculations

---

## Formula Verification Checklist

Before delivering any Excel file:

- [ ] **Run recalc.py** - Ensure zero formula errors
- [ ] **Test sample references** - Verify 2-3 formulas pull correct values
- [ ] **Check column mapping** - Confirm Excel columns match (col 64 = BL)
- [ ] **Verify row offsets** - Excel is 1-indexed (DataFrame row 5 = Excel row 6)
- [ ] **Handle edge cases** - Test with zero, negative, large values
- [ ] **Check cross-sheet refs** - Verify sheet names in formulas
- [ ] **Validate inputs** - Ensure dropdowns and validations work

---

## Troubleshooting

### recalc.py fails with macro error
```bash
# Initialize LibreOffice once
soffice --headless --terminate_after_init
# Then retry recalc
```

### Large file performance
```python
# For reading: use read_only mode
wb = load_workbook('huge.xlsx', read_only=True)

# For writing: use write_only mode
wb = Workbook(write_only=True)
ws = wb.create_sheet()
for row in data:
    ws.append(row)

# For pandas: specify columns/rows
df = pd.read_excel('huge.xlsx', usecols='A:E', nrows=1000)
```

### Formulas show as text
- Ensure cell format is not "Text"
- Formula must start with `=`
- Check for leading spaces

### Date parsing issues
```python
# Force date parsing
df = pd.read_excel('data.xlsx', parse_dates=['Date Column'])

# Or convert after reading
df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
```
