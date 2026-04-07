"""
transcriber.py - Whisper model management and audio transcription.

Wraps openai-whisper to provide:
- Lazy model loading (downloaded on first use, cached locally)
- Single-file and multi-chunk transcription
- Optional timestamp formatting (SRT-style)
- Multi-language support
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import whisper

logger = logging.getLogger(__name__)

# All model sizes supported by openai-whisper
AVAILABLE_MODELS: List[str] = ["tiny", "base", "small", "medium", "large"]

# Approximate VRAM / RAM requirements per model (for user guidance)
MODEL_INFO: Dict[str, str] = {
    "tiny":   "~75 MB  — fastest, least accurate",
    "base":   "~150 MB — good balance (default)",
    "small":  "~500 MB — more accurate, ~2× slower",
    "medium": "~1.5 GB — high accuracy, ~5× slower",
    "large":  "~3 GB   — best accuracy, ~10× slower",
}


class WhisperTranscriber:
    """Manage a Whisper model and expose high-level transcription helpers."""

    def __init__(self, model_name: str = "base") -> None:
        """
        Initialise the transcriber.

        Args:
            model_name: One of ``AVAILABLE_MODELS``. Defaults to ``"base"``.

        Raises:
            ValueError: If an unknown model name is supplied.
        """
        if model_name not in AVAILABLE_MODELS:
            raise ValueError(
                f"Unknown model '{model_name}'. "
                f"Choose from: {', '.join(AVAILABLE_MODELS)}"
            )
        self.model_name = model_name
        self._model = None  # loaded lazily

        info = MODEL_INFO.get(model_name, "")
        logger.info("Transcriber configured — model: '%s'  %s", model_name, info)

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def load_model(self) -> None:
        """
        Load (and if necessary download) the Whisper model into memory.

        The model is cached in ``~/.cache/whisper`` on first download so
        subsequent runs are fast.
        """
        logger.info("Loading Whisper model '%s' (first run may download it) ...", self.model_name)
        self._model = whisper.load_model(self.model_name)
        logger.info("Model '%s' loaded successfully.", self.model_name)

    # ------------------------------------------------------------------
    # Core transcription
    # ------------------------------------------------------------------

    def transcribe_file(
        self,
        audio_path: str,
        language: Optional[str] = None,
        verbose: bool = False,
    ) -> dict:
        """
        Transcribe a single audio file with Whisper.

        Args:
            audio_path: Path to a WAV (or any Whisper-compatible) file.
            language: ISO-639-1 language code (e.g. ``"en"``, ``"fr"``).
                      ``None`` triggers automatic language detection.
            verbose: Pass ``True`` to let Whisper print its own progress.

        Returns:
            Whisper result dict containing at minimum ``"text"`` and
            ``"segments"`` keys.
        """
        if self._model is None:
            self.load_model()

        path_name = Path(audio_path).name
        logger.info("Transcribing: %s", path_name)

        kwargs: dict = {"verbose": verbose}
        if language:
            kwargs["language"] = language
            logger.info("Language override: %s", language)
        else:
            logger.info("Language: auto-detect")

        result = self._model.transcribe(audio_path, **kwargs)
        logger.info("Finished transcribing: %s", path_name)
        return result

    # ------------------------------------------------------------------
    # Multi-chunk transcription
    # ------------------------------------------------------------------

    def transcribe_chunks(
        self,
        chunk_paths: List[str],
        language: Optional[str] = None,
        include_timestamps: bool = False,
        verbose: bool = False,
    ) -> dict:
        """
        Transcribe a list of audio chunks and stitch the results together.

        Timestamps from later chunks are offset so they reflect position
        within the full (original) audio timeline.

        Args:
            chunk_paths: Ordered list of WAV file paths.
            language: Language code, or ``None`` for auto-detection.
            include_timestamps: Retain segment timing information.
            verbose: Forward Whisper's internal logging.

        Returns:
            Combined result dict with ``"text"`` and (if requested)
            ``"segments"`` keys.
        """
        if not chunk_paths:
            raise ValueError("chunk_paths must contain at least one entry.")

        if len(chunk_paths) == 1:
            return self.transcribe_file(chunk_paths[0], language=language, verbose=verbose)

        combined_text: List[str] = []
        combined_segments: List[dict] = []
        time_offset: float = 0.0

        for idx, chunk_path in enumerate(chunk_paths):
            logger.info(
                "Processing chunk %d / %d ...", idx + 1, len(chunk_paths)
            )
            result = self.transcribe_file(chunk_path, language=language, verbose=verbose)

            chunk_text = result.get("text", "").strip()
            if chunk_text:
                combined_text.append(chunk_text)

            # Adjust segment timestamps relative to the full timeline
            for segment in result.get("segments", []):
                adjusted = dict(segment)
                adjusted["start"] += time_offset
                adjusted["end"] += time_offset
                combined_segments.append(adjusted)

            # Advance offset by the duration of this chunk's last segment
            segments = result.get("segments", [])
            if segments:
                time_offset += segments[-1]["end"]

        combined: dict = {"text": " ".join(combined_text)}
        if include_timestamps:
            combined["segments"] = combined_segments

        return combined

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def format_transcription(
        self,
        result: dict,
        include_timestamps: bool = False,
    ) -> str:
        """
        Convert a Whisper result dict to a human-readable string.

        When ``include_timestamps=True`` each segment is prefixed with an
        ``[HH:MM:SS.mmm --> HH:MM:SS.mmm]`` stamp, similar to SRT format.

        Args:
            result: Whisper transcription result dict.
            include_timestamps: Emit segment-level timestamps.

        Returns:
            Formatted transcription string.
        """
        if not include_timestamps or "segments" not in result:
            return result.get("text", "").strip()

        lines: List[str] = []
        for segment in result["segments"]:
            start = self._format_timestamp(segment["start"])
            end = self._format_timestamp(segment["end"])
            text = segment.get("text", "").strip()
            lines.append(f"[{start} --> {end}]  {text}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Convert a float number of seconds to ``HH:MM:SS.mmm`` string."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds % 1) * 1000))
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
