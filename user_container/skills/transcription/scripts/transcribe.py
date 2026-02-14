# /// script
# dependencies = ["openai"]
# ///
"""
Transcription Script using OpenAI GPT-4o Transcribe API

Transcribes audio/video files to text using GPT-4o transcription models.

Usage:
    uv run transcribe.py --audio-path <path> [options]

Options:
    --audio-path <path> Path to audio/video file (required).
    --language <code>   Language code (e.g., en, pl). Auto-detected if not specified.
    --prompt "<text>"   Optional prompt to guide transcription (not supported with --diarize).
    --timestamps        Include word-level timestamps (not supported with --diarize).
    --format <type>     Output format: text (default), json, srt, vtt.
    --diarize           Enable speaker diarization (identifies different speakers).

Examples:
    uv run transcribe.py --audio-path recording.mp3
    uv run transcribe.py --audio-path meeting.m4a --language en --prompt "Technical meeting"
    uv run transcribe.py --audio-path video.mp4 --format srt
    uv run transcribe.py --audio-path interview.mp3 --diarize
"""

import argparse
import json
import os
import sys
from pathlib import Path


def get_api_key() -> str:
    """
    Get OpenAI API key from secrets file or environment.
    """
    secrets_file = Path("/app/secrets.json")

    # Try secrets file first
    if secrets_file.exists():
        try:
            with open(secrets_file) as f:
                secrets = json.load(f)
            key = secrets.get("openai_api_key")
            if key:
                return key
        except Exception:
            pass

    # Fallback to environment variable
    return os.getenv("OPENAI_API_KEY")


def transcribe(
    audio_path: str,
    language: str = None,
    prompt: str = None,
    timestamps: bool = False,
    output_format: str = "text",
    diarize: bool = False,
) -> dict:
    """
    Transcribe audio file using OpenAI GPT-4o Transcribe API.

    Args:
        audio_path: Path to audio/video file
        language: Language code (optional, auto-detected)
        prompt: Context prompt to improve accuracy (optional, not supported with diarize)
        timestamps: Include word-level timestamps (not supported with diarize)
        output_format: text, json, srt, or vtt
        diarize: Enable speaker diarization (identifies different speakers)

    Returns:
        dict with status, text, and metadata
    """
    from openai import OpenAI

    path = Path(audio_path)

    if not path.exists():
        return {"status": "error", "error": f"File not found: {audio_path}"}

    # Check file size (API limit is 25MB)
    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > 25:
        return {
            "status": "error",
            "error": f"File too large: {file_size_mb:.1f}MB (max 25MB). Compress or split the file.",
        }

    # Check supported formats
    supported = {".mp3", ".wav", ".m4a", ".webm", ".mp4", ".ogg", ".flac"}
    if path.suffix.lower() not in supported:
        return {
            "status": "error",
            "error": f"Unsupported format: {path.suffix}. Supported: {', '.join(supported)}",
        }

    api_key = get_api_key()
    if not api_key:
        return {"status": "error", "error": "OPENAI_API_KEY not configured"}

    # Warn about incompatible options with diarization
    if diarize:
        if prompt:
            return {
                "status": "error",
                "error": "--prompt is not supported with --diarize. Remove the prompt option.",
            }
        if timestamps:
            return {
                "status": "error",
                "error": "--timestamps is not supported with --diarize. Diarization includes segment timing automatically.",
            }
        if output_format in ["srt", "vtt"]:
            return {
                "status": "error",
                "error": f"--format {output_format} is not supported with --diarize. Use 'text' or 'json'.",
            }

    try:
        client = OpenAI(api_key=api_key)

        if diarize:
            # Use diarization model
            model_name = "gpt-4o-transcribe-diarize"
            with open(audio_path, "rb") as audio_file:
                kwargs = {
                    "model": model_name,
                    "file": audio_file,
                    "response_format": "diarized_json",
                    "chunking_strategy": "auto",
                }

                if language:
                    kwargs["language"] = language

                response = client.audio.transcriptions.create(**kwargs)

            # Build result with speaker segments
            result = {
                "status": "success",
                "provider": "openai",
                "model": model_name,
                "text": response.text,
                "language": getattr(response, "language", language),
                "usage": _extract_usage(response),
            }

            # Extract speaker segments from diarized response
            if hasattr(response, "segments"):
                result["segments"] = [
                    {
                        "speaker": getattr(seg, "speaker", "unknown"),
                        "start": getattr(seg, "start", None),
                        "end": getattr(seg, "end", None),
                        "text": getattr(seg, "text", "").strip(),
                    }
                    for seg in response.segments
                ]

            return result

        else:
            # Use standard transcription model
            model_name = "gpt-4o-transcribe"
            # Determine response format for API
            response_format = "verbose_json" if timestamps or output_format in ["srt", "vtt"] else "json"

            with open(audio_path, "rb") as audio_file:
                kwargs = {
                    "model": model_name,
                    "file": audio_file,
                    "response_format": response_format,
                }

                if language:
                    kwargs["language"] = language
                if prompt:
                    kwargs["prompt"] = prompt

                response = client.audio.transcriptions.create(**kwargs)

            usage = _extract_usage(response)

            # Handle different output formats
            if output_format == "srt":
                return {
                    "status": "success",
                    "provider": "openai",
                    "model": model_name,
                    "format": "srt",
                    "content": _to_srt(response),
                    "language": getattr(response, "language", language),
                    "usage": usage,
                }
            elif output_format == "vtt":
                return {
                    "status": "success",
                    "provider": "openai",
                    "model": model_name,
                    "format": "vtt",
                    "content": _to_vtt(response),
                    "language": getattr(response, "language", language),
                    "usage": usage,
                }
            else:
                result = {
                    "status": "success",
                    "provider": "openai",
                    "model": model_name,
                    "text": response.text,
                    "language": getattr(response, "language", language),
                    "duration_seconds": getattr(response, "duration", None),
                    "usage": usage,
                }

                if timestamps and hasattr(response, "segments"):
                    result["segments"] = [
                        {
                            "start": getattr(seg, "start", None),
                            "end": getattr(seg, "end", None),
                            "text": getattr(seg, "text", ""),
                        }
                        for seg in response.segments
                    ]

                return result

    except Exception as e:
        return {"status": "error", "error": str(e)}


def _extract_usage(response) -> dict:
    """Extract token usage from OpenAI transcription response."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"input_tokens": 0, "output_tokens": 0}

    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
    }


def _to_srt(response) -> str:
    """Convert response to SRT subtitle format."""
    if not hasattr(response, "segments"):
        # If no segments, create single segment from full text
        return f"1\n00:00:00,000 --> 00:00:10,000\n{response.text}\n"

    lines = []
    for i, seg in enumerate(response.segments, 1):
        start = _format_timestamp_srt(getattr(seg, "start", 0))
        end = _format_timestamp_srt(getattr(seg, "end", 0))
        text = getattr(seg, "text", "").strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")

    return "\n".join(lines)


def _to_vtt(response) -> str:
    """Convert response to WebVTT subtitle format."""
    if not hasattr(response, "segments"):
        return f"WEBVTT\n\n00:00:00.000 --> 00:00:10.000\n{response.text}\n"

    lines = ["WEBVTT", ""]
    for seg in response.segments:
        start = _format_timestamp_vtt(getattr(seg, "start", 0))
        end = _format_timestamp_vtt(getattr(seg, "end", 0))
        text = getattr(seg, "text", "").strip()
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def _format_timestamp_srt(seconds: float) -> str:
    """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_timestamp_vtt(seconds: float) -> str:
    """Format seconds to WebVTT timestamp (HH:MM:SS.mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio/video using OpenAI GPT-4o Transcribe API"
    )
    parser.add_argument(
        "--audio-path", required=True, help="Path to audio/video file"
    )
    parser.add_argument(
        "--language", "-l", help="Language code (e.g., en, pl). Auto-detected if not specified."
    )
    parser.add_argument(
        "--prompt", "-p", help="Context prompt to improve accuracy (not supported with --diarize)"
    )
    parser.add_argument(
        "--timestamps", "-t", action="store_true", help="Include word-level timestamps (not supported with --diarize)"
    )
    parser.add_argument(
        "--format", "-f", choices=["text", "json", "srt", "vtt"], default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--diarize", "-d", action="store_true", help="Enable speaker diarization (identifies different speakers)"
    )

    args = parser.parse_args()

    result = transcribe(
        audio_path=getattr(args, 'audio_path', None),
        language=args.language,
        prompt=args.prompt,
        timestamps=args.timestamps,
        output_format=args.format,
        diarize=args.diarize,
    )

    # For SRT/VTT, print raw content if successful
    if result.get("status") == "success" and result.get("format") in ["srt", "vtt"]:
        print(result["content"])
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
