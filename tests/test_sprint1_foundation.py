"""
NTH Transcript Engine — Sprint 1 Foundation Tests
Owner: QA Agent
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from models.transcript import (
    JobStatus,
    SourceType,
    Transcript,
    TranscriptionJob,
    TranscriptSegment,
    VideoMetadata,
    WhisperModel,
)
from ingestion.youtube_handler import VideoIngestionError, YouTubeHandler
from transcription.audio_extractor import (
    AudioExtractionError,
    AudioExtractor,
    FFmpegNotFoundError,
)
from transcription.engine import TranscriptionEngine, TranscriptionError


# ----------------------------- TranscriptSegment -----------------------------

def test_transcript_segment_creation():
    seg = TranscriptSegment(
        segment_id=0,
        start_time=1.5,
        end_time=3.0,
        text="hello world",
    )
    assert seg.segment_id == 0
    assert seg.start_time == 1.5
    assert seg.end_time == 3.0
    assert seg.text == "hello world"
    assert seg.confidence is None


def test_transcript_segment_duration():
    seg = TranscriptSegment(0, 10.0, 12.5, "x")
    assert seg.duration == pytest.approx(2.5)


def test_transcript_segment_formatted_time():
    seg = TranscriptSegment(0, 3661.0, 3725.0, "x")  # 1h 1m 1s -> 1h 2m 5s
    assert seg.formatted_start == "01:01:01"
    assert seg.formatted_end == "01:02:05"


# ------------------------------ VideoMetadata --------------------------------

def test_video_metadata_creation():
    md = VideoMetadata(
        title="Test Video",
        duration_seconds=120.0,
        source_url="https://youtube.com/watch?v=abc",
        source_type=SourceType.YOUTUBE,
        uploader="NTH",
        upload_date="20260409",
        description="desc",
        thumbnail_url="https://img",
        view_count=42,
        language="en",
    )
    assert md.title == "Test Video"
    assert md.duration_seconds == 120.0
    assert md.source_type is SourceType.YOUTUBE
    assert md.uploader == "NTH"
    assert md.upload_date == "20260409"
    assert md.view_count == 42
    assert md.language == "en"


# ----------------------------- TranscriptionJob ------------------------------

def test_transcription_job_defaults():
    job = TranscriptionJob()
    assert isinstance(job.job_id, str) and len(job.job_id) >= 8
    assert job.status is JobStatus.PENDING
    assert job.source_type is SourceType.YOUTUBE
    assert job.whisper_model is WhisperModel.BASE
    assert isinstance(job.created_at, datetime)
    assert job.completed_at is None
    assert job.error_message is None
    assert job.metadata is None


def test_transcription_job_mark_failed():
    job = TranscriptionJob()
    job.mark_failed("boom")
    assert job.status is JobStatus.FAILED
    assert job.error_message == "boom"
    assert isinstance(job.completed_at, datetime)


def test_transcription_job_mark_complete():
    job = TranscriptionJob()
    job.mark_complete()
    assert job.status is JobStatus.COMPLETE
    assert isinstance(job.completed_at, datetime)


# -------------------------------- Transcript ---------------------------------

def test_transcript_word_count():
    t = Transcript(full_text="one two three four five")
    assert t.word_count == 5


def test_transcript_segment_count():
    segs = [TranscriptSegment(i, i, i + 1, "x") for i in range(3)]
    t = Transcript(segments=segs)
    assert t.segment_count == 3


def test_transcript_get_text_in_range():
    segs = [
        TranscriptSegment(0, 0.0, 1.0, "alpha"),
        TranscriptSegment(1, 1.0, 2.0, "beta"),
        TranscriptSegment(2, 2.0, 3.0, "gamma"),
        TranscriptSegment(3, 3.0, 4.0, "delta"),
    ]
    t = Transcript(segments=segs)
    result = t.get_text_in_range(1.0, 3.0)
    assert "beta" in result
    assert "gamma" in result
    assert "alpha" not in result
    assert "delta" not in result


# ----------------------------- YouTubeHandler --------------------------------

def test_youtube_handler_validate_url_valid(tmp_path):
    h = YouTubeHandler(str(tmp_path))
    assert h.validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert h.validate_url("https://youtu.be/dQw4w9WgXcQ") is True
    assert h.validate_url("http://youtube.com/watch?v=abc123") is True
    assert h.validate_url("https://www.youtube.com/shorts/abc123") is True


def test_youtube_handler_validate_url_invalid(tmp_path):
    h = YouTubeHandler(str(tmp_path))
    assert h.validate_url("https://vimeo.com/12345") is False
    assert h.validate_url("not a url") is False
    assert h.validate_url("") is False
    assert h.validate_url("https://example.com/watch?v=abc") is False


def test_youtube_handler_download_invalid_url_raises(tmp_path):
    h = YouTubeHandler(str(tmp_path))
    job = TranscriptionJob()
    with pytest.raises(VideoIngestionError):
        h.download("https://example.com/notyt", job)
    assert job.status is JobStatus.FAILED


# ------------------------------ AudioExtractor -------------------------------

def test_audio_extractor_ffmpeg_check():
    with patch("transcription.audio_extractor.shutil.which", return_value=None):
        with pytest.raises(FFmpegNotFoundError):
            AudioExtractor()


# ---------------------------------- Enums ------------------------------------

def test_source_type_enum_values():
    assert SourceType.YOUTUBE.value == "youtube"
    assert SourceType.LOCAL_FILE.value == "local_file"
    assert SourceType.DIRECT_URL.value == "direct_url"
    assert SourceType.VIMEO.value == "vimeo"


def test_job_status_enum_values():
    expected = {
        "PENDING": "pending",
        "DOWNLOADING": "downloading",
        "EXTRACTING": "extracting",
        "TRANSCRIBING": "transcribing",
        "COMPLETE": "complete",
        "FAILED": "failed",
    }
    for name, value in expected.items():
        assert JobStatus[name].value == value
