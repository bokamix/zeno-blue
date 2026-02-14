# /// script
# dependencies = ["pillow"]
# ///
"""
Image Info Script

Extracts metadata from image files without using Vision API.
Returns dimensions, format, color mode, file size, and EXIF data.

Usage:
    uv run info.py <image_path> [--exif]

Options:
    --exif  Include full EXIF data (camera settings, GPS, etc.)

Examples:
    uv run info.py photo.jpg
    uv run info.py photo.jpg --exif
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def get_exif_data(image: Image.Image) -> dict:
    """Extract EXIF data from image."""
    exif_data = {}

    try:
        exif = image._getexif()
        if exif is None:
            return {}

        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)

            # Handle GPS data specially
            if tag == "GPSInfo":
                gps_data = {}
                for gps_tag_id, gps_value in value.items():
                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_data[gps_tag] = str(gps_value)
                exif_data["GPSInfo"] = gps_data
            else:
                # Convert bytes and other non-serializable types to strings
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8", errors="ignore")
                    except Exception:
                        value = str(value)
                elif not isinstance(value, (str, int, float, bool, type(None))):
                    value = str(value)

                exif_data[tag] = value

    except Exception as e:
        exif_data["_error"] = str(e)

    return exif_data


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_image_info(image_path: str, include_exif: bool = False) -> dict:
    """
    Get image metadata.

    Args:
        image_path: Path to image file
        include_exif: Include full EXIF data

    Returns:
        dict with image metadata
    """
    path = Path(image_path)

    if not path.exists():
        return {"status": "error", "error": f"File not found: {image_path}"}

    try:
        # File system info
        stat = path.stat()
        file_info = {
            "filename": path.name,
            "path": str(path.absolute()),
            "size_bytes": stat.st_size,
            "size_human": format_file_size(stat.st_size),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

        # Image info
        with Image.open(path) as img:
            image_info = {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "mode_description": {
                    "1": "Black and white (1-bit)",
                    "L": "Grayscale (8-bit)",
                    "P": "Palette (8-bit)",
                    "RGB": "RGB color (24-bit)",
                    "RGBA": "RGB with alpha (32-bit)",
                    "CMYK": "CMYK color",
                    "YCbCr": "YCbCr color",
                    "LAB": "LAB color",
                    "HSV": "HSV color",
                    "I": "Integer pixels (32-bit)",
                    "F": "Float pixels (32-bit)",
                }.get(img.mode, img.mode),
                "is_animated": getattr(img, "is_animated", False),
                "n_frames": getattr(img, "n_frames", 1),
            }

            # Calculate megapixels
            megapixels = (img.width * img.height) / 1_000_000
            image_info["megapixels"] = round(megapixels, 2)

            # Aspect ratio
            from math import gcd
            divisor = gcd(img.width, img.height)
            image_info["aspect_ratio"] = f"{img.width // divisor}:{img.height // divisor}"

            # EXIF data
            if include_exif:
                exif = get_exif_data(img)
                if exif:
                    image_info["exif"] = exif

            # Quick EXIF summary (always included if available)
            try:
                exif = img._getexif()
                if exif:
                    quick_exif = {}
                    # Common useful EXIF fields
                    exif_mapping = {
                        271: "camera_make",
                        272: "camera_model",
                        306: "date_taken",
                        37377: "shutter_speed",
                        37378: "aperture",
                        34855: "iso",
                        37386: "focal_length",
                    }
                    for tag_id, key in exif_mapping.items():
                        if tag_id in exif:
                            value = exif[tag_id]
                            if isinstance(value, bytes):
                                value = value.decode("utf-8", errors="ignore")
                            quick_exif[key] = str(value)
                    if quick_exif:
                        image_info["exif_summary"] = quick_exif
            except Exception:
                pass

        return {
            "status": "success",
            "file": file_info,
            "image": image_info,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run info.py <image_path> [--exif]")
        print()
        print("Extract metadata from image files.")
        print()
        print("Options:")
        print("  --exif  Include full EXIF data (camera, GPS, etc.)")
        print()
        print("Examples:")
        print("  uv run info.py photo.jpg")
        print("  uv run info.py photo.jpg --exif")
        sys.exit(1)

    image_path = sys.argv[1]
    include_exif = "--exif" in sys.argv

    result = get_image_info(image_path, include_exif)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
