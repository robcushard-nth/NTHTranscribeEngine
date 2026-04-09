# QA Agent — NTH Transcript Engine Sprint 1

## Role
You are the QA Agent for Sprint 1 of the NTH Transcript Engine.
You write all tests — backend agent does not write tests.
You run all QA gates. You validate frozen assets.
You report DoD checklist results to PM Agent.
You do not write source code. You write test code only.

Read `CLAUDE_MASTER_SPRINT_1.md` completely before writing tests.

---

## Frozen Asset Verification

Sprint 1 creates new files only. No prior sprint files exist.
After Sprint 1 commit, run to confirm clean state:
```bash
git diff --name-only HEAD~1 HEAD
```
Expected: Only Sprint 1 files appear. Report any unexpected files to PM Agent.

---

## QA Gate 1 — Hard Gate Tests

Run after PM Agent confirms all backend Phase deliverables are complete.

```bash
pytest tests/test_sprint1_foundation.py::test_transcription_job_defaults -v
pytest tests/test_sprint1_foundation.py::test_transcript_segment_creation -v
pytest tests/test_sprint1_foundation.py::test_youtube_handler_validate_url_valid -v
```

**These three tests are hard gates. Sprint halts on any failure.**
Report result to PM Agent: PASS or FAIL with full pytest output.

---

## QA Gate 2 — Full Suite

```bash
pytest tests/test_sprint1_foundation.py -v --tb=long
```

Minimum 12 tests must pass. 15 expected.
Report: total count, pass count, fail count, any failures with tracebacks.

---

## Full Test File — Copy-Paste Ready

**File:** `tests/test_sprint1_foundation.py`
**Write this file exactly as shown. Do not modify or summarize.**

```python
"""
NTH Transcript Engine — Sprint 1 Foundation Tests
QA Agent | Sprint 1
Tests: 15
Hard Gates: test_transcription_job_defaults, test_transcript_segment_creation,
            test_youtube_handler_validate_url_valid
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


# ===========================================================================
# MODEL TESTS — TranscriptSegment
# ===========================================================================

def test_transcript_segment_creation():
    """HARD GATE: TranscriptSegment initializes with correct fields."""
    from models.transcript import TranscriptSegment
    seg = TranscriptSegment(
        segment_id=0,
        start_time=10.5,
        end_time=25.0,
        text="This is a test segment."
    )
    assert seg.segment_id == 0
    assert seg.start_time == 10.5
    assert seg.end_time == 25.0
    assert seg.text == "This is a test segment."
    assert seg.confidence is None


def test_transcript_segment_duration():
    """duration property returns end_time minus start_time."""
    from models.transcript import TranscriptSegment
    seg = TranscriptSegment(segment_id=1, start_time=5.0, end_time=15.5, text="hello")
    assert seg.duration == pytest.approx(10.5)


def test_transcript_segment_formatted_time():
    """formatted_start and formatted_end return HH:MM:SS format."""
    from models.transcript import TranscriptSegment
    seg = TranscriptSegment(segment_id=2, start_time=3661.0, end_time=3725.0, text="test")
    assert seg.formatted_start == "01:01:01"
    assert seg.formatted_end == "01:02:05"


def test_transcript_segment_zero_start():
    """Segment at time zero formats correctly."""
    from models.transcript import TranscriptSegment
    seg = TranscriptSegment(segment_id=0, start_time=0.0, end_time=5.0, text="intro")
    assert seg.formatted_start == "00:00:00"
    assert seg.duration == pytest.approx(5.0)


# ===========================================================================
# MODEL TESTS — VideoMetadata
# ===========================================================================

def test_video_metadata_creation():
    """VideoMetadata initializes with all required and optional fields."""
    from models.transcript import VideoMetadata, SourceType
    meta = VideoMetadata(
        title="Test Video",
        duration_seconds=3600.0,
        source_url="https://www.youtube.com/watch?v=test123",
        source_type=SourceType.YOUTUBE,
        uploader="TestChannel",
        upload_date="20240101"
    )
    assert meta.title == "Test Video"
    assert meta.duration_seconds == 3600.0
    assert meta.source_type == SourceType.YOUTUBE
    assert meta.uploader == "TestChannel"
    assert meta.upload_date == "20240101"
    assert meta.thumbnail_url is None
    assert meta.view_count is None


# ===========================================================================
# MODEL TESTS — TranscriptionJob
# ===========================================================================

def test_transcription_job_defaults():
    """HARD GATE: TranscriptionJob generates UUID and defaults to PENDING status."""
    from models.transcript import TranscriptionJob, JobStatus, SourceType, WhisperModel
    job = TranscriptionJob(source_url="https://www.youtube.com/watch?v=test")
    assert job.job_id is not None
    assert len(job.job_id) == 36  # UUID4 format
    assert job.status == JobStatus.PENDING
    assert job.source_type == SourceType.YOUTUBE
    assert job.whisper_model == WhisperModel.BASE
    assert job.created_at is not None
    assert job.completed_at is None
    assert job.error_message is None


def test_transcription_job_mark_failed():
    """mark_failed sets FAILED status, records error message, and sets completed_at."""
    from models.transcript import TranscriptionJob, JobStatus
    job = TranscriptionJob(source_url="https://www.youtube.com/watch?v=test")
    job.mark_failed("Network timeout")
    assert job.status == JobStatus.FAILED
    assert job.error_message == "Network timeout"
    assert job.completed_at is not None
    assert isinstance(job.completed_at, datetime)


def test_transcription_job_mark_complete():
    """mark_complete sets COMPLETE status and records completed_at."""
    from models.transcript import TranscriptionJob, JobStatus
    job = TranscriptionJob(source_url="https://www.youtube.com/watch?v=test")
    job.mark_complete()
    assert job.status == JobStatus.COMPLETE
    assert job.completed_at is not None


def test_transcription_job_unique_ids():
    """Two TranscriptionJobs have different job_ids."""
    from models.transcript import TranscriptionJob
    job1 = TranscriptionJob(source_url="https://www.youtube.com/watch?v=aaa")
    job2 = TranscriptionJob(source_url="https://www.youtube.com/watch?v=bbb")
    assert job1.job_id != job2.job_id


# ===========================================================================
# MODEL TESTS — Transcript
# ===========================================================================

def test_transcript_word_count():
    """word_count property returns correct word count from full_text."""
    from models.transcript import Transcript
    t = Transcript(full_text="The quick brown fox jumps over the lazy dog")
    assert t.word_count == 9


def test_transcript_segment_count():
    """segment_count property returns the number of segments."""
    from models.transcript import Transcript, TranscriptSegment
    segs = [
        TranscriptSegment(segment_id=i, start_time=float(i*5),
                          end_time=float(i*5 + 4), text=f"segment {i}")
        for i in range(5)
    ]
    t = Transcript(segments=segs)
    assert t.segment_count == 5


def test_transcript_get_text_in_range():
    """get_text_in_range returns only segments within the specified time window."""
    from models.transcript import Transcript, TranscriptSegment
    segs = [
        TranscriptSegment(segment_id=0, start_time=0.0, end_time=5.0, text="intro"),
        TranscriptSegment(segment_id=1, start_time=5.0, end_time=10.0, text="middle"),
        TranscriptSegment(segment_id=2, start_time=10.0, end_time=15.0, text="outro"),
    ]
    t = Transcript(segments=segs)
    result = t.get_text_in_range(5.0, 10.0)
    assert "middle" in result
    assert "intro" not in result
    assert "outro" not in result


# ===========================================================================
# ENUM TESTS
# ===========================================================================

def test_source_type_enum_values():
    """SourceType enum contains all expected values."""
    from models.transcript import SourceType
    assert SourceType.YOUTUBE.value == "youtube"
    assert SourceType.LOCAL_FILE.value == "local_file"
    assert SourceType.DIRECT_URL.value == "direct_url"
    assert SourceType.VIMEO.value == "vimeo"


def test_job_status_enum_values():
    """JobStatus enum contains all expected values."""
    from models.transcript import JobStatus
    assert JobStatus.PENDING.value == "pending"
    assert JobStatus.DOWNLOADING.value == "downloading"
    assert JobStatus.TRANSCRIBING.value == "transcribing"
    assert JobStatus.COMPLETE.value == "complete"
    assert JobStatus.FAILED.value == "failed"


# ===========================================================================
# INGESTION TESTS — YouTubeHandler
# ===========================================================================

def test_youtube_handler_validate_url_valid():
    """HARD GATE: validate_url returns True for valid YouTube URLs."""
    from ingestion.youtube_handler import YouTubeHandler
    handler = YouTubeHandler(download_dir="./downloads")
    assert handler.validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert handler.validate_url("https://youtu.be/dQw4w9WgXcQ") is True
    assert handler.validate_url("https://youtube.com/shorts/abc123") is True


def test_youtube_handler_validate_url_invalid():
    """validate_url returns False for non-YouTube URLs and garbage input."""
    from ingestion.youtube_handler import YouTubeHandler
    handler = YouTubeHandler(download_dir="./downloads")
    assert handler.validate_url("https://vimeo.com/123456") is False
    assert handler.validate_url("not a url at all") is False
    assert handler.validate_url("https://www.google.com") is False
    assert handler.validate_url("") is False


# ===========================================================================
# TRANSCRIPTION TESTS — AudioExtractor
# ===========================================================================

def test_audio_extractor_ffmpeg_check():
    """FFmpegNotFoundError is raised when FFmpeg is not on PATH (mocked)."""
    from transcription.audio_extractor import FFmpegNotFoundError
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")
        with pytest.raises(FFmpegNotFoundError):
            from transcription.audio_extractor import AudioExtractor
            # Force re-instantiation to trigger _verify_ffmpeg
            extractor = AudioExtractor.__new__(AudioExtractor)
            extractor._verify_ffmpeg()
```

---

## Full Test Run Command

```bash
pytest tests/test_sprint1_foundation.py -v --tb=long 2>&1
```

Expected output summary:
```
15 passed in X.Xs
```

---

## Definition of Done Checklist — QA Report to PM Agent

```
DoD Sprint 1 — QA Agent Final Report
============================================================
[ ] models/transcript.py — importable, 6 classes verified
[ ] ingestion/__init__.py — exists
[ ] ingestion/youtube_handler.py — YouTubeHandler importable
[ ] transcription/__init__.py — exists
[ ] transcription/audio_extractor.py — AudioExtractor importable
[ ] transcription/engine.py — TranscriptionEngine importable
[ ] requirements.txt — 5 dependencies
[ ] .env.example — 8 env vars
[ ] tests/test_sprint1_foundation.py — delivered by QA Agent
[ ] Total tests: 15
[ ] Tests passing: ___
[ ] Tests failing: ___
[ ] Hard gate: test_transcription_job_defaults — PASS / FAIL
[ ] Hard gate: test_transcript_segment_creation — PASS / FAIL
[ ] Hard gate: test_youtube_handler_validate_url_valid — PASS / FAIL
[ ] git diff clean — Sprint 1 files only
============================================================
OVERALL: PASS / FAIL
```

---

## Git Commit (PM Agent Directs — QA Agent Confirms)

```bash
git add -A
git commit -m "sprint1: foundation complete"
```

---

## 🏁 Sprint 1 Milestone Statement

Sprint 1 establishes the operational foundation of the NTH Transcript Engine.
The data model layer is live and frozen. The YouTube ingestion pipeline is
operational. The audio extraction and faster-whisper transcription engine are
wired and verified. Sprint 1 delivers 15 tests at 100% pass rate.

The platform is ready for Sprint 2: API Layer — FastAPI endpoints, job queue,
and SQLite transcript persistence.
