# /// script
# dependencies = ["pillow"]
# ///
"""
Image Preprocessing Script

Prepares images for Vision API analysis: resize, crop, convert format, enhance.
Useful when images are too large or need optimization before analysis.

Usage:
    uv run preprocess.py <image_path> <output_path> [options]

Options:
    --resize WxH        Resize to specific dimensions (e.g., 1920x1080)
    --max-size SIZE     Resize keeping aspect ratio, max dimension SIZE (e.g., 2048)
    --max-mb MB         Reduce quality until file is under MB megabytes
    --crop X,Y,W,H      Crop region (x, y, width, height)
    --format FORMAT     Convert to format (jpeg, png, webp)
    --quality Q         JPEG/WebP quality 1-100 (default: 85)
    --grayscale         Convert to grayscale
    --enhance           Auto-enhance (contrast, sharpness)

Examples:
    uv run preprocess.py large.png small.jpg --max-size 2048
    uv run preprocess.py photo.jpg cropped.jpg --crop 100,100,500,500
    uv run preprocess.py scan.png enhanced.png --enhance --grayscale
    uv run preprocess.py huge.png compressed.jpg --max-mb 5
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps


def resize_to_dimensions(img: Image.Image, width: int, height: int) -> Image.Image:
    """Resize image to exact dimensions."""
    return img.resize((width, height), Image.Resampling.LANCZOS)


def resize_max_dimension(img: Image.Image, max_size: int) -> Image.Image:
    """Resize keeping aspect ratio, max dimension = max_size."""
    ratio = max_size / max(img.width, img.height)
    if ratio >= 1:
        return img  # Already smaller
    new_width = int(img.width * ratio)
    new_height = int(img.height * ratio)
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def crop_region(img: Image.Image, x: int, y: int, width: int, height: int) -> Image.Image:
    """Crop a region from image."""
    return img.crop((x, y, x + width, y + height))


def enhance_image(img: Image.Image) -> Image.Image:
    """Auto-enhance image (contrast, sharpness, color)."""
    # Auto contrast
    img = ImageOps.autocontrast(img, cutoff=1)

    # Slight sharpness boost
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.2)

    # Slight contrast boost
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.1)

    return img


def save_with_max_size(img: Image.Image, output_path: str, max_mb: float, initial_quality: int = 85) -> int:
    """Save image, reducing quality until under max_mb. Returns final quality used."""
    max_bytes = max_mb * 1024 * 1024
    quality = initial_quality
    path = Path(output_path)

    # Determine format
    fmt = path.suffix.lower()
    if fmt in [".jpg", ".jpeg"]:
        save_format = "JPEG"
    elif fmt == ".webp":
        save_format = "WebP"
    else:
        # For PNG, we can't reduce quality, so just save
        img.save(output_path, optimize=True)
        return 100

    while quality >= 10:
        img.save(output_path, format=save_format, quality=quality, optimize=True)
        if path.stat().st_size <= max_bytes:
            return quality
        quality -= 5

    return quality


def preprocess_image(
    input_path: str,
    output_path: str,
    resize: str = None,
    max_size: int = None,
    max_mb: float = None,
    crop: str = None,
    output_format: str = None,
    quality: int = 85,
    grayscale: bool = False,
    enhance: bool = False,
) -> dict:
    """
    Preprocess an image file.

    Args:
        input_path: Path to input image
        output_path: Path for output image
        resize: Resize to WxH (e.g., "1920x1080")
        max_size: Resize keeping aspect ratio, max dimension
        max_mb: Reduce quality until file is under this many MB
        crop: Crop region as "X,Y,W,H"
        output_format: Convert to format (jpeg, png, webp)
        quality: JPEG/WebP quality 1-100
        grayscale: Convert to grayscale
        enhance: Auto-enhance image

    Returns:
        dict with status and output info
    """
    path = Path(input_path)

    if not path.exists():
        return {"status": "error", "error": f"File not found: {input_path}"}

    try:
        img = Image.open(path)
        original_size = (img.width, img.height)
        original_mode = img.mode

        # Convert to RGB if saving as JPEG (JPEG doesn't support alpha)
        out_path = Path(output_path)
        if out_path.suffix.lower() in [".jpg", ".jpeg"] and img.mode in ["RGBA", "P"]:
            img = img.convert("RGB")

        # Apply operations in order

        # 1. Crop first (before resize)
        if crop:
            try:
                x, y, w, h = map(int, crop.split(","))
                img = crop_region(img, x, y, w, h)
            except ValueError:
                return {"status": "error", "error": f"Invalid crop format: {crop}. Use X,Y,W,H"}

        # 2. Resize
        if resize:
            try:
                w, h = map(int, resize.lower().split("x"))
                img = resize_to_dimensions(img, w, h)
            except ValueError:
                return {"status": "error", "error": f"Invalid resize format: {resize}. Use WxH"}
        elif max_size:
            img = resize_max_dimension(img, max_size)

        # 3. Grayscale
        if grayscale:
            img = img.convert("L")

        # 4. Enhance
        if enhance:
            # Convert back to RGB for enhancement if grayscale
            if img.mode == "L":
                img = img.convert("RGB")
                img = enhance_image(img)
                img = img.convert("L")
            else:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img = enhance_image(img)

        # 5. Save
        if max_mb:
            final_quality = save_with_max_size(img, output_path, max_mb, quality)
        else:
            # Determine format
            fmt = out_path.suffix.lower()
            save_kwargs = {"optimize": True}

            if fmt in [".jpg", ".jpeg"]:
                save_kwargs["format"] = "JPEG"
                save_kwargs["quality"] = quality
            elif fmt == ".webp":
                save_kwargs["format"] = "WebP"
                save_kwargs["quality"] = quality
            elif fmt == ".png":
                save_kwargs["format"] = "PNG"

            img.save(output_path, **save_kwargs)
            final_quality = quality

        # Get output info
        output_stat = out_path.stat()

        return {
            "status": "success",
            "input": {
                "path": str(path.absolute()),
                "size": original_size,
                "mode": original_mode,
            },
            "output": {
                "path": str(out_path.absolute()),
                "size": (img.width, img.height),
                "mode": img.mode,
                "file_size_bytes": output_stat.st_size,
                "file_size_mb": round(output_stat.st_size / (1024 * 1024), 2),
                "quality": final_quality if out_path.suffix.lower() in [".jpg", ".jpeg", ".webp"] else None,
            },
            "operations": {
                "cropped": crop is not None,
                "resized": resize is not None or max_size is not None,
                "grayscale": grayscale,
                "enhanced": enhance,
                "compressed": max_mb is not None,
            },
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    if len(sys.argv) < 3:
        print("Usage: uv run preprocess.py <input> <output> [options]")
        print()
        print("Preprocess images for Vision API analysis.")
        print()
        print("Options:")
        print("  --resize WxH        Resize to dimensions (e.g., 1920x1080)")
        print("  --max-size SIZE     Max dimension keeping aspect ratio")
        print("  --max-mb MB         Compress until under MB megabytes")
        print("  --crop X,Y,W,H      Crop region")
        print("  --format FORMAT     Output format (jpeg, png, webp)")
        print("  --quality Q         JPEG/WebP quality 1-100 (default: 85)")
        print("  --grayscale         Convert to grayscale")
        print("  --enhance           Auto-enhance image")
        print()
        print("Examples:")
        print("  uv run preprocess.py large.png small.jpg --max-size 2048")
        print("  uv run preprocess.py photo.jpg crop.jpg --crop 100,100,500,500")
        print("  uv run preprocess.py huge.png small.jpg --max-mb 5")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # Parse options
    resize = None
    max_size = None
    max_mb = None
    crop = None
    output_format = None
    quality = 85
    grayscale = False
    enhance = False

    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--resize" and i + 1 < len(sys.argv):
            resize = sys.argv[i + 1]
            i += 2
        elif arg == "--max-size" and i + 1 < len(sys.argv):
            max_size = int(sys.argv[i + 1])
            i += 2
        elif arg == "--max-mb" and i + 1 < len(sys.argv):
            max_mb = float(sys.argv[i + 1])
            i += 2
        elif arg == "--crop" and i + 1 < len(sys.argv):
            crop = sys.argv[i + 1]
            i += 2
        elif arg == "--format" and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1]
            i += 2
        elif arg == "--quality" and i + 1 < len(sys.argv):
            quality = int(sys.argv[i + 1])
            i += 2
        elif arg == "--grayscale":
            grayscale = True
            i += 1
        elif arg == "--enhance":
            enhance = True
            i += 1
        else:
            i += 1

    result = preprocess_image(
        input_path,
        output_path,
        resize=resize,
        max_size=max_size,
        max_mb=max_mb,
        crop=crop,
        output_format=output_format,
        quality=quality,
        grayscale=grayscale,
        enhance=enhance,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
