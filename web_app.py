"""
web_app.py - Flask web interface for the Speech-to-Text converter.

Provides a browser-based UI to upload audio files and receive
transcriptions without using the command line.

Usage:
    python web_app.py
    # Then open http://localhost:5000 in your browser.

Environment variables:
    STT_HOST        Bind address  (default: 0.0.0.0)
    STT_PORT        Port number   (default: 5000)
    STT_MODEL       Whisper model (default: base)
    STT_UPLOAD_DIR  Upload dir    (default: ./uploads)
    STT_OUTPUT_DIR  Output dir    (default: ./outputs)
"""

import logging
import os
import sys
import threading
import uuid
from pathlib import Path
from typing import Dict

from flask import Flask, jsonify, render_template, request, send_file

from audio_utils import (
    check_ffmpeg,
    cleanup_temp_files,
    convert_to_wav,
    get_audio_duration,
    split_audio_into_chunks,
    validate_input_file,
)
from transcriber import AVAILABLE_MODELS, WhisperTranscriber

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------

app = Flask(__name__)

UPLOAD_DIR = Path(os.getenv("STT_UPLOAD_DIR", "uploads"))
OUTPUT_DIR = Path(os.getenv("STT_OUTPUT_DIR", "outputs"))
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB hard limit
LARGE_FILE_THRESHOLD_SECONDS = 25 * 60

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory job registry  {job_id: {...}}
_jobs: Dict[str, dict] = {}
_jobs_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Background processing
# ---------------------------------------------------------------------------

def _process_job(
    job_id: str,
    input_path: str,
    model_name: str,
    language: str | None,
    include_timestamps: bool,
) -> None:
    """Run the full transcription pipeline in a background thread."""

    def _set(key: str, value) -> None:
        with _jobs_lock:
            _jobs[job_id][key] = value

    _set("status", "processing")
    _set("progress", "Converting audio to WAV …")

    temp_wav: str | None = None
    chunk_paths: list[str] = []

    try:
        temp_wav = convert_to_wav(input_path)

        duration_s = get_audio_duration(temp_wav)
        _set("progress", f"Audio: {duration_s / 60:.1f} min — loading Whisper model …")

        if duration_s > LARGE_FILE_THRESHOLD_SECONDS:
            chunk_paths = split_audio_into_chunks(temp_wav)
        else:
            chunk_paths = [temp_wav]

        transcriber = WhisperTranscriber(model_name=model_name)
        transcriber.load_model()

        _set("progress", "Transcribing … (this may take a while)")

        result = transcriber.transcribe_chunks(
            chunk_paths=chunk_paths,
            language=language,
            include_timestamps=include_timestamps,
        )

        formatted = transcriber.format_transcription(
            result, include_timestamps=include_timestamps
        )

        # Persist result to disk so the download endpoint can serve it
        out_file = OUTPUT_DIR / f"{job_id}.txt"
        out_file.write_text(formatted, encoding="utf-8")

        with _jobs_lock:
            _jobs[job_id].update(
                {
                    "status": "completed",
                    "progress": "Transcription complete!",
                    "text": formatted,
                    "output_file": out_file.name,
                }
            )
        logger.info("Job %s completed.", job_id)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s failed: %s", job_id, exc)
        with _jobs_lock:
            _jobs[job_id].update({"status": "failed", "error": str(exc)})

    finally:
        # Remove only chunk files that are separate from temp_wav
        separate_chunks = [p for p in chunk_paths if p != temp_wav]
        cleanup_temp_files(separate_chunks, temp_wav)
        # Remove the uploaded source file
        try:
            Path(input_path).unlink(missing_ok=True)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Render the upload UI."""
    return render_template("index.html", models=AVAILABLE_MODELS)


@app.route("/transcribe", methods=["POST"])
def transcribe():
    """
    Accept a multipart upload and start a background transcription job.

    Form fields
    -----------
    file        : audio file (required)
    model       : whisper model name (optional, default: base)
    language    : ISO-639-1 code (optional)
    timestamps  : "true" / "false" (optional)
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in request."}), 400

    upload = request.files["file"]
    if not upload.filename:
        return jsonify({"error": "No filename supplied."}), 400

    # Extract and sanitise the file extension only — we generate a UUID name.
    ext = Path(upload.filename).suffix.lower()
    safe_name = f"{uuid.uuid4()}{ext}"
    upload_path = UPLOAD_DIR / safe_name

    upload.save(str(upload_path))

    # Validate the file format before queueing
    try:
        validate_input_file(str(upload_path))
    except (FileNotFoundError, ValueError) as exc:
        upload_path.unlink(missing_ok=True)
        return jsonify({"error": str(exc)}), 400

    # Parse optional parameters
    model_name = request.form.get("model", "base")
    if model_name not in AVAILABLE_MODELS:
        model_name = "base"

    language_raw = request.form.get("language", "").strip()
    language = language_raw if language_raw else None

    include_timestamps = request.form.get("timestamps", "false").lower() == "true"

    # Create job record
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "status": "queued",
            "progress": "Queued — waiting to start …",
            "text": None,
            "output_file": None,
            "error": None,
        }

    # Start processing in background thread
    thread = threading.Thread(
        target=_process_job,
        args=(job_id, str(upload_path), model_name, language, include_timestamps),
        daemon=True,
    )
    thread.start()

    logger.info("Job %s queued (model=%s, lang=%s, ts=%s).", job_id, model_name, language, include_timestamps)
    return jsonify({"job_id": job_id}), 202


@app.route("/status/<job_id>")
def job_status(job_id: str):
    """Return the current status of a transcription job."""
    with _jobs_lock:
        job = _jobs.get(job_id)

    if job is None:
        return jsonify({"error": "Job not found."}), 404

    # Don't include the full text in status polls — use /download instead.
    return jsonify(
        {
            "status": job["status"],
            "progress": job["progress"],
            "error": job.get("error"),
            "has_result": job["text"] is not None,
            "output_file": job.get("output_file"),
            # Include text in completed responses for the UI preview
            "text": job["text"] if job["status"] == "completed" else None,
        }
    )


@app.route("/download/<filename>")
def download_file(filename: str):
    """Serve a completed transcription file as a download."""
    # Prevent path traversal by using only the bare filename component
    safe_filename = Path(filename).name
    file_path = OUTPUT_DIR / safe_filename

    if not file_path.exists():
        return jsonify({"error": "File not found."}), 404

    return send_file(
        str(file_path),
        mimetype="text/plain",
        as_attachment=True,
        download_name="transcription.txt",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not check_ffmpeg():
        error_msg = "ERROR: ffmpeg not found on PATH.\n"
        if sys.platform == "win32":
            error_msg += (
                "  Windows: See WINDOWS_SETUP.md for detailed installation instructions\n"
                "           OR download from https://ffmpeg.org/download.html"
            )
        else:
            error_msg += (
                "  Ubuntu/Debian: sudo apt install ffmpeg\n"
                "  macOS:         brew install ffmpeg"
            )
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    host = os.getenv("STT_HOST", "0.0.0.0")
    port = int(os.getenv("STT_PORT", "5000"))

    print(f"\nSpeech-to-Text Web UI starting on http://{host}:{port}")
    print("Press Ctrl-C to stop.\n")

    app.run(host=host, port=port, debug=False, threaded=True)
