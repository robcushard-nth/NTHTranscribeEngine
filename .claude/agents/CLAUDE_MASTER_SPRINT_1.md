# CLAUDE_MASTER_SPRINT_1.md
**Project:** NTH Transcript Engine
**Sprint:** 1 — Foundation
**Module:** Data Models · YouTube Ingestion · Audio Extraction · Transcription Engine
**Author:** William "Rob" Cushard — NTH AI Dynamics
**Git Author:** `robcushard-nth <rob.cushard@nthsimplesolution.com>`
**Repo:** `C:\Users\RobCushard\NTH_TRANSCRIPT_ENGINE\`
**Agent Path:** `.claude\agents\`
**Date:** 2026-04-09
**Status:** 🔴 NOT STARTED

---

## Sprint Mission

Sprint 1 builds the operational core of the NTH Transcript Engine. This sprint
delivers four things: (1) the authoritative data models that all future sprints
import, (2) the YouTube ingestion handler using yt-dlp, (3) the audio extraction
pipeline using FFmpeg, and (4) the faster-whisper transcription engine.

At the end of Sprint 1, an operator can call a single Python function with a
YouTube URL and receive a structured Transcript object with timestamped segments.
No API, no UI — those come in Sprints 2 and 3. This sprint is the engine.

The data models defined in `models/transcript.py` are frozen after Sprint 1.
All future sprints import from them. The backend agent owns this file and delivers
it first. No other agent modifies it.

---

## Scope Boundary

### IN SCOPE — Sprint 1
- `models/transcript.py` — authoritative dataclasses (frozen after delivery)
- `ingestion/youtube_handler.py` — yt-dlp YouTube download + metadata extraction
- `ingestion/__init__.py` — package init
- `transcription/audio_extractor.py` — FFmpeg audio extraction from video file
- `transcription/engine.py` — faster-whisper transcription engine
- `transcription/__init__.py` — package init
- `requirements.txt` — pinned dependencies
- `.env.example` — environment config template
- `tests/test_sprint1_foundation.py` — QA agent writes this file
- Minimum 12 pytest tests

### OUT OF SCOPE — Sprint 1
- FastAPI, uvicorn, any HTTP layer (Sprint 2)
- NiceGUI or any UI panel (Sprint 3)
- SQLite repository or persistence (Sprint 2)
- Local file ingestion handler (Sprint 4)
- Direct URL ingestion (Sprint 4)
- Export formats: TXT, SRT, JSON, DOCX (Sprint 5)
- Vimeo, Rumble, or other platform handlers (Sprint 4)
- CUDA or GPU acceleration configuration (post-Sprint 3)

---

## Authoritative Data Models
**File:** `models/transcript.py`
**Owner:** Backend Agent (Sprint 1) — FROZEN after delivery
**Rule:** All future sprints import from this file. No other sprint modifies these classes.

```python
# models/transcript.py
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
    metadata: Optional[VideoMetadata] = None
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
```

---

## Module Specifications

### Module 1: `ingestion/youtube_handler.py`

**Responsibility:** Accept a YouTube URL, validate it, download the video to
the downloads directory, extract metadata, and return a populated
TranscriptionJob with VideoMetadata attached.

**Key behaviors:**
- Validate URL format before attempting download
- Use yt-dlp with `format='bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'`
- Extract: title, duration, uploader, upload_date, description, thumbnail_url, view_count
- Store video file in `DOWNLOAD_DIR/{job_id}/video.{ext}`
- Update `job.status` to `JobStatus.DOWNLOADING` at start, set `job.video_file_path` on success
- Raise `VideoIngestionError` on failure (define in this module)
- Support `--no-playlist` flag to prevent accidental playlist downloads

**Interface:**
```python
class YouTubeHandler:
    def __init__(self, download_dir: str): ...
    def download(self, url: str, job: TranscriptionJob) -> TranscriptionJob: ...
    def validate_url(self, url: str) -> bool: ...
    def _extract_metadata(self, info_dict: dict) -> VideoMetadata: ...

class VideoIngestionError(Exception): ...
```

---

### Module 2: `transcription/audio_extractor.py`

**Responsibility:** Accept a video file path, extract audio as 16kHz mono WAV
(Whisper's required format), and return the path to the extracted audio file.

**Key behaviors:**
- Use FFmpeg via `subprocess` (not ffmpeg-python library — use direct subprocess call)
- Output format: 16kHz, mono, WAV — `ffmpeg -i input -ar 16000 -ac 1 -f wav output`
- Store audio in same job directory as video: `{job_dir}/audio.wav`
- Verify FFmpeg is on PATH at module import time — raise `FFmpegNotFoundError` if missing
- Update `job.status` to `JobStatus.EXTRACTING`
- Set `job.audio_file_path` on success
- Raise `AudioExtractionError` on subprocess failure

**Interface:**
```python
class AudioExtractor:
    def __init__(self): ...
    def extract(self, video_path: str, output_dir: str, job: TranscriptionJob) -> str: ...
    def _verify_ffmpeg(self) -> None: ...

class AudioExtractionError(Exception): ...
class FFmpegNotFoundError(Exception): ...
```

---

### Module 3: `transcription/engine.py`

**Responsibility:** Accept an audio file path and a WhisperModel enum value,
run faster-whisper transcription, and return a complete Transcript object.

**Key behaviors:**
- Initialize `WhisperModel` from environment variable `WHISPER_MODEL` (default: `base`)
- Use `WHISPER_DEVICE` and `WHISPER_COMPUTE_TYPE` from env
- Update `job.status` to `JobStatus.TRANSCRIBING`
- Build `TranscriptSegment` list from Whisper segment output
- Assemble `full_text` by joining all segment texts with spaces
- Record `processing_duration_seconds` (wall clock time)
- Set `language_detected` from Whisper's detected language
- Raise `TranscriptionError` on engine failure

**Interface:**
```python
class TranscriptionEngine:
    def __init__(self, model_name: str = "base", device: str = "cpu",
                 compute_type: str = "int8"): ...
    def transcribe(self, audio_path: str, job: TranscriptionJob,
                   metadata: Optional[VideoMetadata] = None) -> Transcript: ...
    def _build_segments(self, whisper_segments) -> list[TranscriptSegment]: ...

class TranscriptionError(Exception): ...
```

---

## Directory Structure After Sprint 1

```
NTH_TRANSCRIPT_ENGINE/
├── CLAUDE.md                          ← Exists (pre-sprint)
├── CLAUDE_MASTER_SPRINT_1.md          ← Exists (this file)
├── .claude/
│   └── agents/
│       ├── pm-agent.md                ← NEW (Sprint 1)
│       ├── backend-agent.md           ← NEW (Sprint 1)
│       ├── frontend-agent.md          ← NEW (Sprint 1)
│       └── qa-agent.md                ← NEW (Sprint 1)
├── models/
│   └── transcript.py                  ← NEW (Sprint 1) — FROZEN after delivery
├── ingestion/
│   ├── __init__.py                    ← NEW (Sprint 1)
│   └── youtube_handler.py             ← NEW (Sprint 1)
├── transcription/
│   ├── __init__.py                    ← NEW (Sprint 1)
│   ├── audio_extractor.py             ← NEW (Sprint 1)
│   └── engine.py                      ← NEW (Sprint 1)
├── tests/
│   └── test_sprint1_foundation.py     ← NEW (Sprint 1) — QA agent writes this
├── requirements.txt                   ← NEW (Sprint 1)
├── .env.example                       ← NEW (Sprint 1)
└── downloads/                         ← NEW (Sprint 1, created at runtime)
```

---

## requirements.txt (Exact Content)

```
# NTH Transcript Engine — Sprint 1 Dependencies
yt-dlp>=2024.1.0
faster-whisper>=1.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

> **Note:** FastAPI, uvicorn, NiceGUI added in Sprint 2 and Sprint 3 respectively.

---

## Test Requirements

**Minimum tests:** 12
**Test file:** `tests/test_sprint1_foundation.py`
**Written by:** QA Agent — backend agent does not write tests

| # | Test Name | What It Validates |
|---|---|---|
| 1 | `test_transcript_segment_creation` | TranscriptSegment initializes with correct fields |
| 2 | `test_transcript_segment_duration` | duration property returns end - start |
| 3 | `test_transcript_segment_formatted_time` | formatted_start / formatted_end return HH:MM:SS |
| 4 | `test_video_metadata_creation` | VideoMetadata initializes with all fields |
| 5 | `test_transcription_job_defaults` | TranscriptionJob generates UUID, defaults to PENDING |
| 6 | `test_transcription_job_mark_failed` | mark_failed sets FAILED status and error_message |
| 7 | `test_transcription_job_mark_complete` | mark_complete sets COMPLETE status and completed_at |
| 8 | `test_transcript_word_count` | word_count property returns correct count |
| 9 | `test_transcript_segment_count` | segment_count property returns correct count |
| 10 | `test_transcript_get_text_in_range` | get_text_in_range filters segments by time window |
| 11 | `test_youtube_handler_validate_url_valid` | validate_url returns True for valid YouTube URLs |
| 12 | `test_youtube_handler_validate_url_invalid` | validate_url returns False for non-YouTube URLs |
| 13 | `test_audio_extractor_ffmpeg_check` | FFmpegNotFoundError raised when FFmpeg missing (mocked) |
| 14 | `test_source_type_enum_values` | SourceType enum has expected values |
| 15 | `test_job_status_enum_values` | JobStatus enum has expected values |

**Hard Gate Tests** (sprint halts if these fail):
- `test_transcription_job_defaults` — data model integrity check
- `test_transcript_segment_creation` — segment model integrity check
- `test_youtube_handler_validate_url_valid` — ingestion gateway check

---

## Definition of Done

- [ ] `models/transcript.py` delivered — all 6 dataclasses/enums present and importable
- [ ] `ingestion/__init__.py` delivered
- [ ] `ingestion/youtube_handler.py` delivered — YouTubeHandler and VideoIngestionError present
- [ ] `transcription/__init__.py` delivered
- [ ] `transcription/audio_extractor.py` delivered — AudioExtractor, FFmpegNotFoundError, AudioExtractionError present
- [ ] `transcription/engine.py` delivered — TranscriptionEngine and TranscriptionError present
- [ ] `requirements.txt` delivered with all 5 dependencies
- [ ] `.env.example` delivered with all 6 env vars
- [ ] `tests/test_sprint1_foundation.py` delivered — minimum 12 tests
- [ ] All 15 tests pass: `pytest tests/test_sprint1_foundation.py -v`
- [ ] Hard gate tests all PASS
- [ ] `git diff --name-only` shows only Sprint 1 files (no frozen files modified — N/A Sprint 1)
- [ ] `from models.transcript import Transcript, TranscriptionJob, TranscriptSegment` succeeds
- [ ] `from ingestion.youtube_handler import YouTubeHandler` succeeds
- [ ] `from transcription.engine import TranscriptionEngine` succeeds
- [ ] git commit issued: `sprint1: foundation complete`

---

## Frozen Assets — Sprint 1

Sprint 1 is the first sprint. There are no prior frozen assets.

After Sprint 1 completes, the following files are **permanently frozen**:
- `models/transcript.py` — all classes, all field names, all enums

Future sprints may only extend by adding new files. The models file is never modified.

---

## Permitted File Modifications — Sprint 1

None. Sprint 1 creates all new files.

---

## Downstream Sprint Readiness

Sprint 2 (API Layer) requires Sprint 1 to deliver:
- `models/transcript.py` — imports TranscriptionJob, Transcript, JobStatus
- `ingestion/youtube_handler.py` — called by API job submission endpoint
- `transcription/engine.py` — called by background job processor
- `requirements.txt` — Sprint 2 appends FastAPI, uvicorn, dependencies

Sprint 2 agent must run `pytest tests/test_sprint1_foundation.py -v` and confirm
all tests pass before writing any Sprint 2 code.

---

## PM Agent Launch Prompt

```
You are the PM Agent for Sprint 1 of the NTH Transcript Engine.

Read CLAUDE_MASTER_SPRINT_1.md completely before taking any action.

This is Sprint 1 — the Foundation sprint. There are no prior sprints to validate.
Your first action is to confirm the repo structure is clean and no files from the
Sprint 1 scope already exist (if they do, report to the user before proceeding).

Execute in this sequence:
1. Instruct Backend Agent to deliver files in this order:
   a. models/transcript.py (FIRST — all other modules import from this)
   b. requirements.txt and .env.example
   c. ingestion/__init__.py and ingestion/youtube_handler.py
   d. transcription/__init__.py
   e. transcription/audio_extractor.py
   f. transcription/engine.py

2. After backend delivery, run import verification:
   python -c "from models.transcript import Transcript, TranscriptionJob, TranscriptSegment, TranscriptSegment, VideoMetadata, SourceType, JobStatus, WhisperModel; print('MODELS OK')"
   python -c "from ingestion.youtube_handler import YouTubeHandler, VideoIngestionError; print('INGESTION OK')"
   python -c "from transcription.audio_extractor import AudioExtractor, FFmpegNotFoundError, AudioExtractionError; print('EXTRACTOR OK')"
   python -c "from transcription.engine import TranscriptionEngine, TranscriptionError; print('ENGINE OK')"

3. QA Gate 1: Instruct QA Agent to write tests/test_sprint1_foundation.py
   and run: pytest tests/test_sprint1_foundation.py -v
   HARD GATE: test_transcription_job_defaults, test_transcript_segment_creation,
   test_youtube_handler_validate_url_valid must all PASS.
   If any hard gate test fails — halt sprint, instruct backend agent to fix.

4. QA Gate 2 (Final): Run full test suite:
   pytest tests/test_sprint1_foundation.py -v --tb=short
   Minimum 12 tests must pass. 15 expected.

5. Report Definition of Done — explicit PASS/FAIL for every checklist item.

6. On full DoD PASS, issue git commit:
   git add -A
   git commit -m "sprint1: foundation complete"

Critical constraint: models/transcript.py is delivered FIRST and is frozen
immediately after the QA Agent confirms all model tests pass.
No other file may define or redefine the dataclasses in that file.
```
