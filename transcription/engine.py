"""
NTH Transcript Engine — faster-whisper Transcription Engine
Sprint 1 | Owner: Backend Agent
"""

import os
import time
from pathlib import Path
from typing import Optional

from models.transcript import (
    JobStatus,
    Transcript,
    TranscriptionJob,
    TranscriptSegment,
    VideoMetadata,
)


class TranscriptionError(Exception):
    """Raised when faster-whisper transcription fails."""


class TranscriptionEngine:
    """Wraps faster-whisper to produce structured Transcript objects."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        self.model_name = model_name or os.getenv("WHISPER_MODEL", "base")
        self.device = device or os.getenv("WHISPER_DEVICE", "cpu")
        self.compute_type = compute_type or os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        self._model = None  # lazy-loaded

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel as FWModel
        except ImportError as e:
            raise TranscriptionError(f"faster-whisper not installed: {e}") from e

        try:
            self._model = FWModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        except Exception as e:
            raise TranscriptionError(f"Failed to load Whisper model: {e}") from e
        return self._model

    def transcribe(
        self,
        audio_path: str,
        job: TranscriptionJob,
        metadata: Optional[VideoMetadata] = None,
    ) -> Transcript:
        if not Path(audio_path).exists():
            msg = f"Audio file does not exist: {audio_path}"
            job.mark_failed(msg)
            raise TranscriptionError(msg)

        job.status = JobStatus.TRANSCRIBING
        start_wall = time.time()

        try:
            model = self._load_model()
            segments_iter, info = model.transcribe(audio_path, beam_size=5)
            segments = self._build_segments(segments_iter)
        except TranscriptionError:
            raise
        except Exception as e:
            job.mark_failed(f"Transcription failed: {e}")
            raise TranscriptionError(f"Transcription failed: {e}") from e

        elapsed = time.time() - start_wall
        full_text = " ".join(seg.text.strip() for seg in segments).strip()

        transcript = Transcript(
            job_id=job.job_id,
            metadata=metadata or job.metadata,
            segments=segments,
            full_text=full_text,
            language_detected=getattr(info, "language", None),
            whisper_model_used=self.model_name,
            processing_duration_seconds=elapsed,
        )
        job.mark_complete()
        return transcript

    def _build_segments(self, whisper_segments) -> list[TranscriptSegment]:
        out: list[TranscriptSegment] = []
        for idx, seg in enumerate(whisper_segments):
            out.append(
                TranscriptSegment(
                    segment_id=idx,
                    start_time=float(getattr(seg, "start", 0.0) or 0.0),
                    end_time=float(getattr(seg, "end", 0.0) or 0.0),
                    text=str(getattr(seg, "text", "")),
                    confidence=getattr(seg, "avg_logprob", None),
                )
            )
        return out
