---
name: transcription
description: "Transcribe audio/video files to text using AI. Use when user wants to: convert speech to text, transcribe recordings, meetings, podcasts, or interviews, extract text from audio/video files, create subtitles or captions, identify speakers in recordings. Supports MP3, WAV, M4A, WEBM, MP4, OGG formats. Features: speaker diarization."
license: MIT
---

# Transcription Skill

Transcribe audio and video files to text using AI speech-to-text model.

## Usage

```bash
uv run transcribe.py --audio-path <path> [options]
```

**Options:**
- `--audio-path <path>` - Path to audio/video file (required).
- `--language <code>` - Language code (e.g., en, pl, de). Auto-detected if not specified.
- `--prompt "<text>"` - Optional prompt to guide transcription (e.g., technical terms, names).
- `--timestamps` - Include word-level timestamps in output.
- `--format <type>` - Output format: text (default), json, srt, vtt.
- `--diarize` - Enable speaker diarization (identifies different speakers).

## Examples

### Basic Transcription

```bash
# Simple transcription
uv run transcribe.py --audio-path recording.mp3

# With language hint and custom prompt
uv run transcribe.py --audio-path meeting.m4a --language en --prompt "Discussion about Kubernetes and Docker"

# Generate SRT subtitles
uv run transcribe.py --audio-path video.mp4 --format srt > subtitles.srt

# With timestamps
uv run transcribe.py --audio-path podcast.mp3 --timestamps --format json
```

### Speaker Diarization

Identify different speakers in a recording:

```bash
# Transcribe with speaker identification
uv run transcribe.py --audio-path interview.mp3 --diarize

# With language hint
uv run transcribe.py --audio-path meeting.m4a --diarize --language en
```

**Note:** `--diarize` cannot be combined with `--prompt`, `--timestamps`, or `--format srt/vtt`.

---

## Output Formats

### Standard Output (default)

```json
{
  "status": "success",
  "provider": "openai",
  "model": "gpt-4o-transcribe",
  "text": "The transcribed text...",
  "language": "en",
  "duration_seconds": 125.4
}
```

### Diarized Output

```json
{
  "status": "success",
  "provider": "openai",
  "model": "gpt-4o-transcribe-diarize",
  "text": "Full transcription text...",
  "language": "en",
  "segments": [
    {"speaker": "speaker_0", "text": "Hello, how are you?", "start": 0.0, "end": 2.5},
    {"speaker": "speaker_1", "text": "I'm doing great, thanks!", "start": 2.6, "end": 4.2}
  ]
}
```

---

## Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| MP3 | .mp3 | Most common, recommended |
| WAV | .wav | Uncompressed, larger files |
| M4A | .m4a | Apple format, good quality |
| WEBM | .webm | Web format |
| MP4 | .mp4 | Video with audio track |
| OGG | .ogg | Open format |
| FLAC | .flac | Lossless audio |

**File size limit:** 25MB.

---

## Model Comparison

| Feature | Standard | Diarization |
|---------|----------|-------------|
| Prompt support | Yes | No |
| Timestamps | Yes | Included in segments |
| Subtitle formats | srt, vtt | No |
| Speaker labels | No | Yes |
| Best for | General use | Meetings, interviews |

---

## Example Workflows

### Workflow 1: Transcribe Meeting Recording

```bash
# 1. Check file info
ls -la meeting.mp3

# 2. Transcribe with context
uv run transcribe.py --audio-path meeting.mp3 --prompt "Meeting with John, Sarah, and Mike about Q4 budget"

# 3. Save to file
uv run transcribe.py --audio-path meeting.mp3 > meeting_transcript.txt
```

### Workflow 2: Create Video Subtitles

```bash
# 1. Generate SRT subtitles
uv run transcribe.py --audio-path video.mp4 --format srt > video.srt

# 2. Or generate VTT for web
uv run transcribe.py --audio-path video.mp4 --format vtt > video.vtt
```

### Workflow 3: Transcribe Interview with Speakers

```bash
# Identify who said what
uv run transcribe.py --audio-path interview.mp3 --diarize

# Save diarized output
uv run transcribe.py --audio-path interview.mp3 --diarize > interview_with_speakers.json
```

### Workflow 4: Transcribe in Specific Language

```bash
# Force Polish language detection
uv run transcribe.py --audio-path polish_audio.mp3 --language pl

# Include technical terms in prompt for better accuracy
uv run transcribe.py --audio-path technical.mp3 --language en --prompt "Programming terms: API, REST, GraphQL, Kubernetes"
```

---

## Troubleshooting

### "File too large"

Split the audio or compress it:
```bash
# Compress with ffmpeg
ffmpeg -i large.wav -ab 128k compressed.mp3
```

### Poor quality transcription

1. Use `--prompt` with relevant context
2. Specify `--language` explicitly
3. Ensure audio quality is good (minimal background noise)

### API errors

- Check API key is set (OPENAI_API_KEY)
- Verify file exists and is readable
- Check file format is supported

---

## API Reference

```
transcribe(
    audio_path: str,
    language: str = None,
    prompt: str = None,
    timestamps: bool = False,
    output_format: str = "text",
    diarize: bool = False
) -> dict

Returns:
  {
    "status": "success" | "error",
    "provider": "openai",
    "model": "gpt-4o-transcribe" | "gpt-4o-transcribe-diarize",
    "text": str,
    "language": str,
    "duration_seconds": float,       # Standard mode only
    "segments": [...],               # With timestamps or diarize
    "error": str                     # Only if status is "error"
  }
```
