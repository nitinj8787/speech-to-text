#!/usr/bin/env python3
"""
app.py - CLI entry point for the local Speech-to-Text converter.

Usage examples
--------------
Basic (base model, auto-detect language):
    python app.py --input sample.mp3 --output output.txt

Choose a larger model for better accuracy:
    python app.py --input lecture.mp3 --output lecture.txt --model small

Force language and add timestamps:
    python app.py --input speech.mp3 --output speech.txt --language en --timestamps

Keep temporary files (useful for debugging):
    python app.py --input audio.mp3 --output result.txt --no-cleanup

Adjust chunk size for very large files (default 10 min):
    python app.py --input long.mp3 --output long.txt --chunk-size 5
"""

import argparse
import logging
import sys
from pathlib import Path

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
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Files longer than this threshold will be chunked
LARGE_FILE_THRESHOLD_SECONDS = 25 * 60  # 25 minutes


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="app.py",
        description=(
            "Local Speech-to-Text converter powered by OpenAI Whisper.\n"
            "Runs entirely offline — no API key required."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--input", "-i",
        required=True,
        metavar="FILE",
        help="Path to the input audio file (MP3, WAV, M4A, OGG, FLAC …)",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        metavar="FILE",
        help="Path where the transcription text file will be written.",
    )
    parser.add_argument(
        "--model", "-m",
        default="base",
        choices=AVAILABLE_MODELS,
        metavar="NAME",
        help=(
            f"Whisper model size — one of: {', '.join(AVAILABLE_MODELS)}. "
            "Larger models are more accurate but slower and need more RAM. "
            "(default: base)"
        ),
    )
    parser.add_argument(
        "--language", "-l",
        default=None,
        metavar="CODE",
        help=(
            "ISO-639-1 language code of the audio, e.g. 'en', 'fr', 'es', 'de'. "
            "Omit to let Whisper auto-detect the language."
        ),
    )
    parser.add_argument(
        "--timestamps",
        action="store_true",
        help="Include [HH:MM:SS.mmm --> HH:MM:SS.mmm] timestamps in the output.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=10,
        metavar="MINUTES",
        help=(
            "Length (in minutes) of each audio chunk when splitting large files. "
            "(default: 10)"
        ),
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Do not delete temporary WAV and chunk files after processing.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show Whisper's internal per-segment progress.",
    )

    return parser


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def save_transcription(text: str, output_path: str) -> None:
    """Write the transcription string to a UTF-8 text file."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    logger.info("Transcription saved → %s", output_path)


def print_banner(title: str) -> None:
    """Print a simple visual banner to stdout."""
    border = "=" * 62
    print(f"\n{border}")
    print(f"  {title}")
    print(border)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Orchestrate the full speech-to-text pipeline."""
    parser = build_parser()
    args = parser.parse_args()

    print_banner("Speech-to-Text Converter  •  Powered by OpenAI Whisper")

    # ------------------------------------------------------------------ #
    # 1. Pre-flight checks                                                #
    # ------------------------------------------------------------------ #
    logger.info("Checking system dependencies ...")
    if not check_ffmpeg():
        error_msg = "ffmpeg was not found on PATH.\n\n"
        if sys.platform == "win32":
            error_msg += (
                "  Windows: See WINDOWS_SETUP.md for detailed installation instructions\n"
                "           OR download from https://ffmpeg.org/download.html and add to PATH\n"
            )
        else:
            error_msg += (
                "  Install on Ubuntu/Debian :  sudo apt install ffmpeg\n"
                "  Install on macOS         :  brew install ffmpeg\n"
            )
        logger.error(error_msg)
        sys.exit(1)
    logger.info("ffmpeg OK.")

    # ------------------------------------------------------------------ #
    # 2. Validate input                                                   #
    # ------------------------------------------------------------------ #
    try:
        input_path = validate_input_file(args.input)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Input validation failed: %s", exc)
        sys.exit(1)

    file_size_mb = input_path.stat().st_size / (1024 ** 2)
    logger.info("Input  : %s  (%.1f MB)", input_path, file_size_mb)
    logger.info("Output : %s", args.output)
    logger.info("Model  : %s", args.model)

    # ------------------------------------------------------------------ #
    # 3. Pipeline                                                         #
    # ------------------------------------------------------------------ #
    temp_wav: str | None = None
    chunk_paths: list[str] = []

    try:
        # -- 3a. Convert to 16 kHz mono WAV --------------------------------
        temp_wav = convert_to_wav(str(input_path))

        # -- 3b. Inspect duration and decide on chunking -------------------
        duration_s = get_audio_duration(temp_wav)
        duration_min = duration_s / 60.0
        logger.info("Audio duration : %.1f minutes (%.0f seconds)", duration_min, duration_s)

        chunk_ms = args.chunk_size * 60 * 1000

        if duration_s > LARGE_FILE_THRESHOLD_SECONDS:
            logger.info(
                "Large file (> %d min) — will split into %d-minute chunks.",
                LARGE_FILE_THRESHOLD_SECONDS // 60,
                args.chunk_size,
            )
            chunk_paths = split_audio_into_chunks(temp_wav, chunk_ms)
        else:
            chunk_paths = [temp_wav]

        # -- 3c. Load model and transcribe ---------------------------------
        transcriber = WhisperTranscriber(model_name=args.model)
        transcriber.load_model()

        logger.info("Starting transcription ...")
        logger.info("-" * 50)

        result = transcriber.transcribe_chunks(
            chunk_paths=chunk_paths,
            language=args.language,
            include_timestamps=args.timestamps,
            verbose=args.verbose,
        )

        logger.info("-" * 50)
        logger.info("Transcription complete.")

        # -- 3d. Format, display, and save ----------------------------------
        formatted = transcriber.format_transcription(
            result, include_timestamps=args.timestamps
        )

        print_banner("TRANSCRIPTION")
        print(formatted)
        print("=" * 62 + "\n")

        save_transcription(formatted, args.output)

        logger.info("All done!  Output → %s", args.output)

    except RuntimeError as exc:
        logger.error("Processing error: %s", exc)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(130)

    finally:
        # ---------------------------------------------------------------- #
        # 4. Cleanup                                                        #
        # ---------------------------------------------------------------- #
        if not args.no_cleanup:
            # Only clean up actual chunk *files* (not the source temp_wav
            # itself) when chunking produced multiple separate files.
            separate_chunks = [p for p in chunk_paths if p != temp_wav]
            cleanup_temp_files(separate_chunks, temp_wav)
            if temp_wav:
                logger.info("Temporary files cleaned up.")
        else:
            logger.info("--no-cleanup set — temporary files retained.")


if __name__ == "__main__":
    main()
