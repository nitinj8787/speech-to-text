# Speech-to-Text Converter

A fully local, offline Speech-to-Text application powered by **OpenAI Whisper**.  
No cloud dependency, no API key — everything runs on your machine.

---

## Project Structure

```
speech-to-text/
├── app.py            # CLI entry point
├── transcriber.py    # Whisper model logic
├── audio_utils.py    # Audio conversion & chunking
├── web_app.py        # Flask web UI (bonus)
├── templates/
│   └── index.html    # Browser upload page
└── requirements.txt
```

---

## Prerequisites

### 1 · Python 3.10+

```bash
python --version   # must be 3.10 or newer
```

### 2 · ffmpeg

pydub requires ffmpeg to read MP3 and other formats.

| Platform      | Command                                      |
|---------------|----------------------------------------------|
| Ubuntu/Debian | `sudo apt install ffmpeg`                    |
| macOS         | `brew install ffmpeg`                        |
| Windows       | Download from <https://ffmpeg.org/download.html> and add to PATH |

> **Windows users:** If you encounter errors related to pydub or ffmpeg not found, see [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for detailed installation instructions.

---

## Installation

```bash
# 1. Clone / enter the project folder
cd speech-to-text

# 2. Create & activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt
```

> **Note:** `openai-whisper` automatically downloads PyTorch.  
> On first use each Whisper model is downloaded once and cached in `~/.cache/whisper`.

---

## CLI Usage — `app.py`

```bash
# Basic (base model, auto-detect language)
python app.py --input sample.mp3 --output output.txt

# Better accuracy with the small model
python app.py --input lecture.mp3 --output lecture.txt --model small

# Force language + add timestamps
python app.py --input speech.mp3 --output speech.txt --language en --timestamps

# Keep temporary files (useful for debugging)
python app.py --input audio.mp3  --output result.txt --no-cleanup

# Split large files into 5-minute chunks (default: 10)
python app.py --input long.mp3   --output long.txt   --chunk-size 5
```

### All CLI options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--input`      | `-i` | *(required)* | Path to the audio file |
| `--output`     | `-o` | *(required)* | Path to write the `.txt` file |
| `--model`      | `-m` | `base`       | Whisper model: `tiny` `base` `small` `medium` `large` |
| `--language`   | `-l` | auto-detect  | ISO-639-1 code, e.g. `en`, `fr`, `de` |
| `--timestamps` |      | off          | Emit `[HH:MM:SS → HH:MM:SS]` lines |
| `--chunk-size` |      | `10`         | Minutes per chunk for large files |
| `--no-cleanup` |      | off          | Keep intermediate WAV/chunk files |
| `--verbose`    |      | off          | Show Whisper's internal per-segment log |

---

## Web UI — `web_app.py`

```bash
python web_app.py
# Open http://localhost:5000 in your browser
```

The web interface allows you to:
- Drag-and-drop or browse for an audio file
- Choose a Whisper model and language
- Toggle timestamp inclusion
- View, copy, and download the transcription

Environment variables that control the server:

| Variable        | Default     | Purpose                  |
|-----------------|-------------|--------------------------|
| `STT_HOST`      | `0.0.0.0`   | Bind address             |
| `STT_PORT`      | `5000`      | Port                     |
| `STT_MODEL`     | `base`      | Default Whisper model    |
| `STT_UPLOAD_DIR`| `./uploads` | Temporary upload storage |
| `STT_OUTPUT_DIR`| `./outputs` | Transcription output dir |

---

## Whisper Model Comparison

| Model  | Size   | Speed  | Accuracy |
|--------|--------|--------|----------|
| tiny   | ~75 MB | ×10    | ★★☆☆☆  |
| base   | ~150 MB| ×7     | ★★★☆☆  |
| small  | ~500 MB| ×4     | ★★★★☆  |
| medium | ~1.5 GB| ×2     | ★★★★☆  |
| large  | ~3 GB  | ×1     | ★★★★★  |

---

## Supported Audio Formats

MP3 · WAV · M4A · OGG · FLAC · MP4 · WEBM · AAC · WMA

All formats are converted to **16 kHz mono WAV** before transcription  
(the format Whisper is optimised for).

---

## Example Output (with timestamps)

```
[00:00:00.000 --> 00:00:04.320]  Welcome to the quarterly earnings call.
[00:00:04.320 --> 00:00:09.140]  Today we will discuss our financial results for Q3.
[00:00:09.140 --> 00:00:15.800]  Revenue grew by twelve percent year over year.
```
