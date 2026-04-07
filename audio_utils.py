"""
audio_utils.py - Handles audio file loading, validation, conversion, and chunking.

Supports MP3, WAV, M4A, OGG, FLAC and more via pydub/ffmpeg.
Converts audio to 16 kHz mono WAV, the format Whisper works best with.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from pydub import AudioSegment

logger = logging.getLogger(__name__)

# Audio formats supported by pydub/ffmpeg
SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4", ".webm", ".aac", ".wma"}

# Default chunk length: 10 minutes expressed in milliseconds
DEFAULT_CHUNK_DURATION_MS = 10 * 60 * 1000

# ---------------------------------------------------------------------------
# Well-known Windows ffmpeg installation paths (checked when not on PATH)
# ---------------------------------------------------------------------------

_WINDOWS_FFMPEG_HINTS = [
    r"C:\WorkspaceNj\ffmpeg-8.1\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
]
_WINDOWS_FFPROBE_HINTS = [
    r"C:\WorkspaceNj\ffmpeg-8.1\bin\ffprobe.exe",
    r"C:\ffmpeg\bin\ffprobe.exe",
    r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
]


def _find_executable(name: str, windows_hints: List[str]) -> Optional[str]:
    """
    Return the absolute path to *name* by checking:
    1. The system PATH (all platforms).
    2. A hard-coded list of well-known Windows install locations.

    Returns ``None`` if the executable cannot be found.
    """
    # Check PATH first
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / name
        if candidate.is_file():
            return str(candidate)
        # On Windows the extension may be omitted in PATH entries
        candidate_exe = Path(directory) / (name + ".exe")
        if candidate_exe.is_file():
            return str(candidate_exe)

    # Fall back to well-known Windows locations
    if sys.platform == "win32":
        for hint in windows_hints:
            if Path(hint).is_file():
                return hint

    return None


def configure_ffmpeg() -> Optional[str]:
    """
    Locate ffmpeg/ffprobe and configure pydub to use them.

    Tries the system PATH first; if that fails on Windows, checks the
    well-known installation hints defined in ``_WINDOWS_FFMPEG_HINTS``.

    Returns:
        The resolved ffmpeg path if found, ``None`` otherwise.
    """
    ffmpeg_path = _find_executable("ffmpeg", _WINDOWS_FFMPEG_HINTS)
    ffprobe_path = _find_executable("ffprobe", _WINDOWS_FFPROBE_HINTS)

    if ffmpeg_path:
        AudioSegment.converter = ffmpeg_path
        logger.debug("pydub ffmpeg → %s", ffmpeg_path)

    if ffprobe_path:
        AudioSegment.ffprobe = ffprobe_path
        logger.debug("pydub ffprobe → %s", ffprobe_path)

    return ffmpeg_path


# ---------------------------------------------------------------------------
# Auto-configure pydub on module import (critical for Windows)
# ---------------------------------------------------------------------------

# Configure pydub with ffmpeg as soon as this module is imported.
# This prevents "FileNotFoundError" in pydub.utils when trying to use
# AudioSegment without explicitly calling check_ffmpeg() first.
_auto_configured_path = configure_ffmpeg()
if _auto_configured_path:
    logger.debug("Auto-configured ffmpeg for pydub at module import.")
elif sys.platform == "win32":
    # On Windows, provide helpful guidance if ffmpeg is not found
    logger.warning(
        "ffmpeg not found on PATH or in common Windows locations. "
        "Please install ffmpeg and add it to PATH, or place it in one of: "
        f"{', '.join(_WINDOWS_FFMPEG_HINTS)}"
    )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def check_ffmpeg() -> bool:
    """
    Return True if ffmpeg is available (on PATH or at a known Windows location).

    As a side-effect this function calls :func:`configure_ffmpeg` so that
    pydub is pointed at the correct binary for subsequent audio operations.
    """
    ffmpeg_path = configure_ffmpeg()
    if ffmpeg_path is None:
        return False

    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def validate_input_file(file_path: str) -> Path:
    """
    Validate that the input audio file exists and has a supported extension.

    Args:
        file_path: Path to the audio file to validate.

    Returns:
        Resolved ``Path`` object for the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the format is not supported.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a regular file: {file_path}")

    extension = path.suffix.lower()
    if extension not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported audio format '{extension}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    return path


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

def convert_to_wav(input_path: str, output_dir: Optional[str] = None) -> str:
    """
    Convert any supported audio file to a 16 kHz mono WAV file.

    Whisper performs best on 16 kHz mono PCM audio; this function normalises
    any input to that specification.

    Args:
        input_path: Path to the source audio file.
        output_dir: Directory where the converted WAV will be written.
                    Defaults to the same directory as the input file.

    Returns:
        Absolute path to the converted WAV file.

    Raises:
        RuntimeError: If the conversion fails.
    """
    input_path = Path(input_path)

    if output_dir:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = input_path.parent

    output_path = out_dir / f"{input_path.stem}_16k_mono.wav"

    logger.info("Converting '%s' → 16 kHz mono WAV ...", input_path.name)
    try:
        audio = AudioSegment.from_file(str(input_path))
        audio = audio.set_channels(1)           # mono
        audio = audio.set_frame_rate(16_000)    # 16 kHz
        audio = audio.set_sample_width(2)       # 16-bit PCM
        audio.export(str(output_path), format="wav")
        logger.info("Conversion complete → %s", output_path.name)
        return str(output_path)
    except Exception as exc:
        raise RuntimeError(f"Audio conversion failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Duration / metadata
# ---------------------------------------------------------------------------

def get_audio_duration(file_path: str) -> float:
    """Return the duration of an audio file in seconds."""
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0


# ---------------------------------------------------------------------------
# Chunking (for large files)
# ---------------------------------------------------------------------------

def split_audio_into_chunks(
    wav_path: str,
    chunk_duration_ms: int = DEFAULT_CHUNK_DURATION_MS,
) -> List[str]:
    """
    Split a WAV file into equal-length chunks for memory-efficient processing.

    If the file is shorter than one chunk length it is returned as-is.

    Args:
        wav_path: Path to the (already-converted) WAV file.
        chunk_duration_ms: Max length of each chunk in milliseconds.

    Returns:
        Ordered list of paths to the chunk WAV files (or ``[wav_path]`` if
        no splitting was required).
    """
    audio = AudioSegment.from_wav(wav_path)
    total_ms = len(audio)

    if total_ms <= chunk_duration_ms:
        logger.info("Audio fits in a single chunk — no splitting required.")
        return [wav_path]

    base = Path(wav_path)
    chunk_dir = base.parent / "chunks"
    chunk_dir.mkdir(exist_ok=True)

    chunk_minutes = chunk_duration_ms // 60_000
    logger.info(
        "Large file detected — splitting into %d-minute chunks ...", chunk_minutes
    )

    chunks: List[str] = []
    for idx, start_ms in enumerate(range(0, total_ms, chunk_duration_ms)):
        end_ms = min(start_ms + chunk_duration_ms, total_ms)
        chunk = audio[start_ms:end_ms]
        chunk_path = chunk_dir / f"{base.stem}_chunk_{idx:03d}.wav"
        chunk.export(str(chunk_path), format="wav")
        chunks.append(str(chunk_path))
        logger.info(
            "  Chunk %d/%d → %s",
            idx + 1,
            -(-total_ms // chunk_duration_ms),  # ceiling division
            chunk_path.name,
        )

    logger.info("Split into %d chunks.", len(chunks))
    return chunks


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup_temp_files(chunk_paths: List[str], temp_wav: Optional[str] = None) -> None:
    """
    Remove temporary chunk files and the intermediate WAV conversion.

    Args:
        chunk_paths: List of chunk file paths to delete.
        temp_wav: Path to the temporary WAV conversion to delete (optional).
    """
    for path_str in chunk_paths:
        try:
            Path(path_str).unlink(missing_ok=True)
        except OSError:
            pass

    # Remove empty chunk directory if applicable
    if chunk_paths:
        chunk_dir = Path(chunk_paths[0]).parent
        try:
            if chunk_dir.name == "chunks" and not any(chunk_dir.iterdir()):
                chunk_dir.rmdir()
        except OSError:
            pass

    if temp_wav:
        try:
            Path(temp_wav).unlink(missing_ok=True)
        except OSError:
            pass
