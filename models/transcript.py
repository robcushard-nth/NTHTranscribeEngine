"""
NTH Transcript Engine — Authoritative Data Models
Sprint 1 | Owner: Backend Agent
FROZEN after Sprint 1 delivery. Import only — do not modify.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class SourceType(Enum):
    YOUTUBE = "youtube"
    LOCAL_FILE = "local_file"
    DIRECT_URL = "direct_url"
    VIMEO = "vimeo"


class JobStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    TRANSCRIBING = "transcribing"
    COMPLETE = "complete"
    FAILED = "failed"


class WhisperModel(Enum):
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE_V3 = "large-v3"


@dataclass
class TranscriptSegment:
    """A single timed segment of a transcript."""
    segment_id: int
    start_time: float          # seconds from video start
    end_time: float            # seconds from video start
    text: str                  # transcribed text for this segment
    confidence: Optional[float] = None   # 0.0–1.0 if model provides it

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def formatted_start(self) -> str:
        """Returns HH:MM:SS format."""
        return self._format_time(self.start_time)

    @property
    def formatted_end(self) -> str:
        return self._format_time(self.end_time)

    def _format_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


@dataclass
class VideoMetadata:
    """Metadata extracted from the video source."""
    title: str
    duration_seconds: float
    source_url: str
    source_type: SourceType
    uploader: Optional[str] = None
    upload_date: Optional[str] = None       # YYYYMMDD string from yt-dlp
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    view_count: Optional[int] = None
    language: Optional[str] = None


@dataclass
class TranscriptionJob:
    """Tracks the full lifecycle of a transcription request."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_url: str = ""
    source_type: SourceType = SourceType.YOUTUBE
    whisper_model: WhisperModel = WhisperModel.BASE
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional["VideoMetadata"] = None
    audio_file_path: Optional[str] = None
    video_file_path: Optional[str] = None

    def mark_failed(self, reason: str) -> None:
        self.status = JobStatus.FAILED
        self.error_message = reason
        self.completed_at = datetime.utcnow()

    def mark_complete(self) -> None:
        self.status = JobStatus.COMPLETE
        self.completed_at = datetime.utcnow()


@dataclass
class Transcript:
    """The complete, structured output of a transcription job."""
    transcript_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""
    metadata: Optional[VideoMetadata] = None
    segments: list[TranscriptSegment] = field(default_factory=list)
    full_text: str = ""
    language_detected: Optional[str] = None
    whisper_model_used: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    processing_duration_seconds: Optional[float] = None

    @property
    def segment_count(self) -> int:
        return len(self.segments)

    @property
    def word_count(self) -> int:
        return len(self.full_text.split())

    def get_text_in_range(self, start: float, end: float) -> str:
        """Returns concatenated text from segments within the time range."""
        return " ".join(
            seg.text for seg in self.segments
            if seg.start_time >= start and seg.end_time <= end
        )
