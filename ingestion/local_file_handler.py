"""
NTH Transcript Engine — Local File Ingestion Handler
Sprint 5 | Owner: Backend Agent
"""

import shutil
import unicodedata
from pathlib import Path

from models.transcript import (
    JobStatus,
    SourceType,
    TranscriptionJob,
    VideoMetadata,
)


class LocalFileIngestionError(Exception):
    """Raised when local file ingestion fails."""


_ALLOWED_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv",
    ".mp3", ".wav", ".m4a",
}


def _clean_path(source: str) -> str:
    """Strip wrapping quotes and Unicode format chars (Windows 'Copy as path' inserts U+202A)."""
    s = source.strip().strip('"').strip("'")
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cf")


class LocalFileHandler:
    """Validates and stages local video/audio files for transcription."""

    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def validate_path(self, source: str) -> bool:
        if not isinstance(source, str) or not source.strip():
            return False
        cleaned = _clean_path(source)
        if not cleaned:
            return False
        try:
            p = Path(cleaned)
        except (OSError, ValueError):
            return False
        try:
            if not p.exists() or not p.is_file():
                return False
        except OSError:
            return False
        return p.suffix.lower() in _ALLOWED_EXTENSIONS

    def ingest(self, source: str, job: TranscriptionJob) -> TranscriptionJob:
        if not self.validate_path(source):
            job.mark_failed(f"Invalid local file path: {source}")
            raise LocalFileIngestionError(f"Invalid local file path: {source}")

        src = Path(_clean_path(source))
        job.status = JobStatus.DOWNLOADING
        job.source_url = str(src)
        job.source_type = SourceType.LOCAL_FILE

        job_dir = self.download_dir / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        target = job_dir / f"video{src.suffix.lower()}"
        try:
            shutil.copy2(src, target)
        except (OSError, shutil.SameFileError) as e:
            job.mark_failed(f"Local file copy failed: {e}")
            raise LocalFileIngestionError(f"Local file copy failed: {e}") from e

        job.video_file_path = str(target)
        job.metadata = VideoMetadata(
            title=src.stem,
            duration_seconds=0.0,
            source_url=str(src),
            source_type=SourceType.LOCAL_FILE,
        )
        return job
