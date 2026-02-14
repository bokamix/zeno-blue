---
name: image
description: "Analyze images using Vision API (Claude or GPT-4V). Extract text (OCR), read documents/invoices/receipts, extract tables and chart data, describe images, analyze UI screenshots. Use when user mentions image analysis, photo, screenshot, OCR, extracting text from image, reading a picture, or working with .png, .jpg, .jpeg, .gif, .webp files."
license: Proprietary. LICENSE.txt has complete terms
---

# Image Analysis Skill

Analyze images using Vision API (Claude or GPT-4V). Extract text, data, descriptions, and structured information from any image.

## Quick Reference

| Script | Purpose | API Cost |
|--------|---------|----------|
| `analyze.py` | Vision API analysis | Yes |
| `info.py` | Metadata extraction | No |
| `preprocess.py` | Resize, crop, optimize | No |

## Scripts

### analyze.py - Vision API Analysis

Main script for image understanding. Sends image + prompt to Vision API.

```bash
uv run analyze.py --image-path <path> --prompt "<prompt>"
```

**Output:**
```json
{
  "status": "success",
  "provider": "anthropic",
  "model": "claude-sonnet-4-5-20250929",
  "response": "The image shows...",
  "usage": {"input_tokens": 1523, "output_tokens": 156}
}
```

### info.py - Image Metadata

Extract file and image metadata without API calls.

```bash
uv run info.py <image_path> [--exif]
```

**Output:**
```json
{
  "status": "success",
  "file": {"filename": "photo.jpg", "size_human": "2.3 MB"},
  "image": {"width": 4032, "height": 3024, "format": "JPEG", "megapixels": 12.19}
}
```

### preprocess.py - Image Optimization

Prepare images for analysis (resize, crop, compress).

```bash
uv run preprocess.py <input> <output> [options]
```

**Options:**
- `--max-size 2048` - Resize keeping aspect ratio
- `--resize 1920x1080` - Resize to exact dimensions
- `--max-mb 5` - Compress until under 5MB
- `--crop 100,100,500,500` - Crop region (x, y, width, height)
- `--grayscale` - Convert to grayscale
- `--enhance` - Auto-enhance (contrast, sharpness)
- `--quality 85` - JPEG/WebP quality (1-100)

---

## Prompting Guide

The key to good image analysis is the right prompt. Below are tested prompts for common use cases.

### 1. General Description

**Simple description:**
```
What's in this image? Describe it briefly.
```

**Detailed description:**
```
Describe this image in detail. Include:
- Main subject/objects
- Colors and composition
- Setting/environment
- Notable details
- Overall mood or style
```

**Focused description:**
```
Describe only the [person/building/product/text] in this image.
```

### 2. Text Extraction (Smart OCR)

**All visible text:**
```
Extract all visible text from this image. Return as plain text, preserving the layout where possible.
```

**Screenshot text:**
```
Extract all text visible in this screenshot. Include UI labels, buttons, menu items, and any content text.
```

**Handwritten text:**
```
Transcribe the handwritten text in this image. If any parts are unclear, indicate with [unclear].
```

**Code from screenshot:**
```
Extract the code shown in this screenshot. Return as properly formatted code with correct indentation.
```

**Multi-language:**
```
Extract all text from this image. The text may be in multiple languages. Preserve the original language.
```

### 3. Document Analysis

**Invoice/Receipt:**
```
Extract data from this invoice/receipt. Return as JSON:
{
  "vendor": "",
  "date": "",
  "invoice_number": "",
  "items": [{"name": "", "quantity": 0, "unit_price": 0, "total": 0}],
  "subtotal": 0,
  "tax": 0,
  "total": 0,
  "payment_method": "",
  "notes": ""
}
Include only fields that are visible. Use null for missing values.
```

**Business Card:**
```
Extract contact information from this business card. Return as JSON:
{
  "name": "",
  "title": "",
  "company": "",
  "email": "",
  "phone": "",
  "mobile": "",
  "address": "",
  "website": "",
  "social": {}
}
```

**Form/Application:**
```
Extract all filled-in fields from this form. Return as JSON with field names as keys and their values.
```

**ID Document:**
```
Extract information from this ID document. Return as JSON:
{
  "document_type": "",
  "name": "",
  "date_of_birth": "",
  "id_number": "",
  "expiry_date": "",
  "issuing_authority": ""
}
Note: Only extract visible information. Do not infer or guess missing data.
```

### 4. Table Extraction

**Table to CSV:**
```
Extract the table from this image. Return as CSV format with headers in the first row.
```

**Table to JSON:**
```
Extract the table from this image. Return as JSON array of objects, where each object represents a row with column names as keys.
```

**Complex table:**
```
Extract all tables from this image. For each table:
1. Identify headers (including merged headers)
2. Extract all data rows
3. Return as CSV with clear column separation

If there are multiple tables, separate them with a blank line and label each.
```

### 5. Charts and Graphs

**Bar/Line chart data:**
```
Extract the data from this chart. Return as CSV with columns for labels/dates and values. Include:
- X-axis labels
- Y-axis values (estimate if needed)
- Legend labels if multiple series
```

**Pie chart:**
```
Extract data from this pie chart. Return as CSV with columns: category, value, percentage.
```

**Describe chart:**
```
Describe this chart:
1. Chart type
2. What it shows (title, axes)
3. Key trends or insights
4. Notable data points (max, min, outliers)
```

### 6. UI/Design Analysis

**UI Description:**
```
Describe this user interface:
1. Type of screen/page (login, dashboard, settings, etc.)
2. Main components and their layout
3. Navigation elements
4. Interactive elements (buttons, forms, etc.)
5. Visual style (colors, typography, spacing)
```

**UI Feedback:**
```
Review this UI design and provide feedback on:
1. Usability - Is it intuitive?
2. Visual hierarchy - Is the important content prominent?
3. Consistency - Are elements styled consistently?
4. Accessibility - Any obvious issues (contrast, text size)?
5. Suggestions for improvement
```

**Compare UI versions:**
```
[Run analyze.py twice, then compare responses]
```

### 7. Product/Object Identification

**Product identification:**
```
Identify the products visible in this image. For each product:
- Product type/category
- Brand (if visible)
- Color/variant
- Approximate quantity
```

**Object counting:**
```
Count the [items/people/objects] in this image. Return the total count and describe any groupings or patterns.
```

**Brand/Logo identification:**
```
Identify any brands, logos, or trademarks visible in this image. List each with its location in the image.
```

### 8. Comparison

To compare two images, analyze each separately and compare results:

```bash
# Analyze first image
uv run analyze.py --image-path image1.png --prompt "Describe this image in detail: layout, colors, text, key elements."

# Analyze second image
uv run analyze.py --image-path image2.png --prompt "Describe this image in detail: layout, colors, text, key elements."

# Then compare the descriptions
```

**Difference prompt (single image showing before/after):**
```
This image shows a before/after comparison. Describe the differences between the two versions.
```

### 9. Quality Assessment

**Image quality:**
```
Assess the quality of this image:
1. Sharpness/Focus - Is it in focus?
2. Exposure - Too dark, too bright, or well-exposed?
3. Noise/Grain - Is there visible noise?
4. Composition - Is it well-framed?
5. Overall usability - Is it suitable for [intended purpose]?

Rate overall quality: Poor / Fair / Good / Excellent
```

### 10. Structured Data Extraction

**Generic JSON extraction:**
```
Extract all relevant information from this image and return as structured JSON. Organize logically based on the content type.
```

**Specific schema:**
```
Extract information from this image following this schema:
{
  "field1": "description of what to extract",
  "field2": "description",
  "nested": {
    "subfield": "description"
  }
}
Return valid JSON only.
```

---

## Best Practices

### Prompt Engineering Tips

1. **Be specific** - "Extract invoice data as JSON" beats "What's in this image?"

2. **Provide structure** - When you need structured output, show the expected format

3. **Set constraints** - "Return only the text, no commentary" or "Maximum 100 words"

4. **Handle uncertainty** - "If unclear, indicate with [unclear]" or "Use null for missing values"

5. **One task per prompt** - Don't ask for description AND data extraction AND analysis in one prompt

### Image Preparation

**When to preprocess:**
- Image > 20MB → Use `--max-mb`
- Image > 4096px on any side → Use `--max-size 4096`
- Only part of image relevant → Use `--crop`
- Scanned document looks faded → Use `--enhance`

**Supported formats:**
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)

**Vision API limits:**
- Max file size: ~20MB
- Recommended: < 5MB for faster processing
- Max dimensions: Varies by provider, 4096px is safe

### Cost Optimization

1. **Resize large images** - A 20MP photo doesn't need full resolution for text extraction

2. **Crop when possible** - If you only need data from one corner, crop first

3. **Use info.py first** - Check dimensions and size before sending to API

4. **Batch similar images** - If extracting same data from many images, develop prompt once, then apply

---

## Example Workflows

### Workflow 1: Process Invoices

```bash
# 1. Check image info
uv run info.py invoice_scan.jpg

# 2. If too large, preprocess
uv run preprocess.py invoice_scan.jpg invoice_ready.jpg --max-size 2048 --enhance

# 3. Extract data
uv run analyze.py --image-path invoice_ready.jpg --prompt "Extract invoice data as JSON: vendor, date, items (name, qty, price), total"
```

### Workflow 2: Extract Table from Photo

```bash
# 1. Crop to table area if needed
uv run preprocess.py whiteboard.jpg table_crop.jpg --crop 100,200,800,600

# 2. Enhance for better readability
uv run preprocess.py table_crop.jpg table_ready.jpg --enhance

# 3. Extract as CSV
uv run analyze.py --image-path table_ready.jpg --prompt "Extract the table as CSV format"
```

### Workflow 3: Batch Screenshot Analysis

```bash
# For each screenshot
for img in screenshots/*.png; do
  uv run analyze.py --image-path "$img" --prompt "Extract all visible text" > "${img%.png}.txt"
done
```

### Workflow 4: Document Digitization

```bash
# 1. Check quality
uv run info.py scanned_doc.jpg

# 2. Enhance scanned document
uv run preprocess.py scanned_doc.jpg doc_enhanced.jpg --enhance --grayscale

# 3. Extract text with layout preservation
uv run analyze.py --image-path doc_enhanced.jpg --prompt "Extract all text, preserving paragraph structure and formatting"
```

---

## Troubleshooting

### "File too large"

```bash
# Compress to under 5MB
uv run preprocess.py huge.png smaller.jpg --max-mb 5
```

### "Unsupported format"

Convert to supported format:
```bash
uv run preprocess.py image.bmp image.jpg
```

### Poor text extraction quality

1. Check image resolution - text needs to be readable
2. Try enhancing: `--enhance`
3. Try grayscale for scanned docs: `--grayscale`
4. Crop to relevant area to increase effective resolution

### API errors

- Check API key is set (ANTHROPIC_API_KEY or OPENAI_API_KEY)
- Check MODEL_PROVIDER env matches your API key
- Verify file exists and is readable

### Inconsistent JSON output

Add explicit instructions:
```
Return ONLY valid JSON, no additional text or explanation.
```

Or use JSON code fence:
```
Return the result as JSON in a code block:
```json
{...}
```
```

---

## Integration with Other Skills

### Image → Excel (xlsx skill)

```bash
# Extract table from image
uv run analyze.py --image-path table_photo.jpg --prompt "Extract as CSV" > /workspace/table.csv

# Convert to Excel using xlsx skill
uv run convert.py /workspace/table.csv /workspace/table.xlsx
```

### Image → Document (docx skill)

Extract text from images and include in documents:
```bash
# Extract text
result=$(uv run analyze.py --image-path scan.jpg --prompt "Extract all text")

# Use text in document creation...
```

---

## API Reference

### analyze.py

```
analyze_image(image_path: str, prompt: str) -> dict

Returns:
  {
    "status": "success" | "error",
    "provider": "anthropic" | "openai",
    "model": str,
    "response": str,  # The analysis result
    "usage": {"input_tokens": int, "output_tokens": int},
    "error": str  # Only if status is "error"
  }
```

### info.py

```
get_image_info(image_path: str, include_exif: bool = False) -> dict

Returns:
  {
    "status": "success" | "error",
    "file": {
      "filename": str,
      "path": str,
      "size_bytes": int,
      "size_human": str,
      "modified": str  # ISO timestamp
    },
    "image": {
      "width": int,
      "height": int,
      "format": str,
      "mode": str,
      "megapixels": float,
      "aspect_ratio": str,
      "exif_summary": {...},  # Quick EXIF if available
      "exif": {...}  # Full EXIF if --exif flag
    }
  }
```

### preprocess.py

```
preprocess_image(
    input_path: str,
    output_path: str,
    resize: str = None,        # "WxH"
    max_size: int = None,      # Max dimension
    max_mb: float = None,      # Max file size
    crop: str = None,          # "X,Y,W,H"
    quality: int = 85,         # JPEG/WebP quality
    grayscale: bool = False,
    enhance: bool = False
) -> dict

Returns:
  {
    "status": "success" | "error",
    "input": {"path": str, "size": [w, h], "mode": str},
    "output": {
      "path": str,
      "size": [w, h],
      "mode": str,
      "file_size_bytes": int,
      "file_size_mb": float,
      "quality": int
    },
    "operations": {
      "cropped": bool,
      "resized": bool,
      "grayscale": bool,
      "enhanced": bool,
      "compressed": bool
    }
  }
```
