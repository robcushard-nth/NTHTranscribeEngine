# CLAUDE_MASTER_SPRINT_5.md

**Project:** NTH Transcript Engine
**Sprint:** 5 — Multi-Source Ingestion
**Module:** Local Files · Direct URLs · Vimeo · Source-Type Auto-Detection
**Author:** William "Rob" Cushard — NTH AI Dynamics
**Git Author:** `robcushard-nth <rob.cushard@nthsimplesolution.com>`
**Repo:** `C:\Users\RobCushard\NTHTranscribeEngine\`
**Agent Path:** `.claude\agents\`
**Date:** 2026-04-23
**Status:** READY TO EXECUTE — Requires Sprint 4 COMPLETE

---

## Sprint Mission

Sprint 5 retires the YouTube-only constraint that has gated the engine since Sprint 1. After Sprint 5 the operator can transcribe four kinds of source:

1. **YouTube URL** — already supported, no change.
2. **Local file path** — any `.mp4 / .mov / .mkv / .avi / .webm / .flv / .mp3 / .wav / .m4a` on the operator's own disk. Audio never leaves the host. This is the headline deliverable — sovereign-stack clients have been blocked on it.
3. **Direct video URL** — any `http(s)://...{ext}` that resolves to a video file. Streamed to disk via `httpx` with a 16 MB chunk size.
4. **Vimeo URL** — pulled via `yt-dlp`'s native Vimeo extractor.

Source type is **auto-detected** from the input string. The submission panel keeps a single text field (broadened to "URL or local file path"); the API route dispatches to the right handler. No new endpoint, no breaking change to the request schema.

The transcription pipeline downstream of ingestion is unchanged — `AudioExtractor` and `TranscriptionEngine` already accept any file path.

---

## Scope Boundary

### IN SCOPE — Sprint 5
- `ingestion/local_file_handler.py` — `LocalFileHandler` (validate path + copy/link to `downloads/{job_id}/`)
- `ingestion/url_handler.py` — `DirectURLHandler` (httpx stream download)
- `ingestion/vimeo_handler.py` — `VimeoHandler` (yt-dlp generic extractor)
- `tests/test_sprint5_multi_source.py` — QA Agent writes this, **minimum 14 tests**

### Permitted modifications to frozen files (explicit allowlist — no other change permitted)

| File | Frozen Since | Permitted Modification |
|---|---|---|
| `api/routes/jobs.py` | Sprint 2 | Replace single `_url_validator` with a `_detect_source_type()` dispatcher that walks YouTube → Vimeo → DirectURL → LocalFile validators. The Pydantic schema field stays named `url` for backward-compat; the value is now a generic source identifier. The `TranscriptionJob` constructor receives the detected `SourceType` (no longer hardcoded `YOUTUBE`). |
| `api/job_processor.py` | Sprint 2 | Replace YouTube-only ingestion (`self.youtube.download(...)`) with a switch on `job.source_type` that routes to one of four handlers. Construct the three new handlers in `__init__`. The audio-extraction and transcription stages are untouched. |
| `ui/panels/job_submission_panel.py` | Sprint 3 | Update the input label from `"YouTube URL"` to `"Video Source (URL or local file path)"` and broaden the placeholder. No structural change to the rendering, polling, or state machine. |
| `requirements.txt` | — | No changes — `httpx` and `yt-dlp` are already pinned. |

### OUT OF SCOPE — Sprint 5
- File-upload via the browser (`ui.upload`) — operator pastes a path on the same machine. This is consistent with the local-only / single-host design.
- New REST endpoint for uploads.
- New columns or migrations on the SQLite schema (the existing `source_type` column already supports all four values).
- Audio-only direct file paths bypassing FFmpeg (FFmpeg handles `.mp3 / .wav / .m4a` correctly today).
- Generic page-scraping for arbitrary HTML pages with embedded video — explicitly rejected as security/scope creep.

---

## Frozen Assets — Sprint 5

The following files **must not** be modified. QA Agent verifies via `git diff --name-only HEAD`:

- `models/transcript.py` (frozen forever since Sprint 1)
- `ingestion/__init__.py`
- `ingestion/youtube_handler.py`
- `transcription/audio_extractor.py`
- `transcription/engine.py`
- `storage/repository.py`
- `api/__init__.py`
- `api/main.py`
- `api/middleware/cors.py`
- `api/routes/exports.py`
- `exports/*.py` (all four exporters)
- `ui/__init__.py`
- `ui/app.py`
- `ui/colors.py`
- `ui/panels/history_panel.py`
- `ui/panels/transcript_viewer_panel.py`
- All prior test files: `tests/test_sprint1_foundation.py`, `tests/test_sprint2_api.py`, `tests/test_sprint3_ui.py`, `tests/test_sprint4_exports.py`

---

## Hard Rules

1. **Sprint 1–4 regression runs FIRST.** Zero Sprint 5 code is written before all 59 prior tests pass on a clean run.
2. **`models/transcript.py` is not touched.** The `SourceType` enum already contains `LOCAL_FILE`, `DIRECT_URL`, `VIMEO` — the data model is ready.
3. **`pathlib.Path` everywhere** — no hardcoded separators. Required for Windows paths.
4. **No shell injection.** Local paths are never interpolated into a shell string. FFmpeg is invoked through the existing `AudioExtractor` (list-args, no `shell=True`).
5. **No new request-schema fields** in the public API. Auto-detection from the existing `url` field is the rule.
6. **Backend agent writes zero test code.** QA agent owns `tests/test_sprint5_multi_source.py`.
7. **Local file ingestion never modifies the source.** It copies to `downloads/{job_id}/` (or symlinks where supported); the original file on the operator's disk is read-only from our perspective.
8. **Direct URL handler rejects YouTube and Vimeo URLs** — those have dedicated handlers. Order of validation matters.

---

## Execution Sequence

### Step 0 — Sprint 1–4 Regression (MANDATORY GATE)

```bash
venv/Scripts/python.exe -m pytest tests/test_sprint1_foundation.py tests/test_sprint2_api.py tests/test_sprint3_ui.py tests/test_sprint4_exports.py -v
```

Expected: **59 passed**. Any failure → halt. Report to user. Do not proceed.

---

### Step 1 — Backend Phase 5a: LocalFileHandler

**File:** `ingestion/local_file_handler.py`

```python
"""
NTH Transcript Engine — Local File Ingestion Handler
Sprint 5 | Owner: Backend Agent
"""

import shutil
from pathlib import Path
from typing import Optional

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


class LocalFileHandler:
    """Validates and stages local video/audio files for transcription."""

    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def validate_path(self, source: str) -> bool:
        """Return True if source is an existing file with a supported extension."""
        if not isinstance(source, str) or not source.strip():
            return False
        try:
            p = Path(source.strip())
        except (OSError, ValueError):
            return False
        if not p.exists() or not p.is_file():
            return False
        return p.suffix.lower() in _ALLOWED_EXTENSIONS

    def ingest(self, source: str, job: TranscriptionJob) -> TranscriptionJob:
        """Copy the source file into downloads/{job_id}/ and populate the job."""
        if not self.validate_path(source):
            job.mark_failed(f"Invalid local file path: {source}")
            raise LocalFileIngestionError(f"Invalid local file path: {source}")

        src = Path(source.strip())
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
            duration_seconds=0.0,  # AudioExtractor + Whisper derive duration downstream
            source_url=str(src),
            source_type=SourceType.LOCAL_FILE,
        )
        return job
```

**Self-check:**

```bash
venv/Scripts/python.exe -c "
from ingestion.local_file_handler import LocalFileHandler, LocalFileIngestionError
h = LocalFileHandler(download_dir='./downloads')
assert h.validate_path('/no/such/file.mp4') is False
assert h.validate_path('not-a-path-just-text') is False
assert h.validate_path('') is False
print('Phase 5a: PASS')
"
```

---

### Step 2 — Backend Phase 5b: DirectURLHandler

**File:** `ingestion/url_handler.py`

```python
"""
NTH Transcript Engine — Direct URL Ingestion Handler
Sprint 5 | Owner: Backend Agent
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from models.transcript import (
    JobStatus,
    SourceType,
    TranscriptionJob,
    VideoMetadata,
)


class DirectURLIngestionError(Exception):
    """Raised when direct URL ingestion fails."""


_VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv",
                     ".mp3", ".wav", ".m4a")
_YOUTUBE_HOSTS = ("youtube.com", "youtu.be")
_VIMEO_HOSTS = ("vimeo.com",)
_HTTP_SCHEMES = ("http", "https")
_CHUNK_BYTES = 16 * 1024 * 1024  # 16 MB


class DirectURLHandler:
    """Streams an `http(s)://...{ext}` resource to disk via httpx."""

    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def validate_url(self, url: str) -> bool:
        """Accept http(s):// URLs ending in a known media extension; reject YouTube/Vimeo."""
        if not isinstance(url, str) or not url.strip():
            return False
        try:
            parsed = urlparse(url.strip())
        except ValueError:
            return False
        if parsed.scheme.lower() not in _HTTP_SCHEMES:
            return False
        host = (parsed.netloc or "").lower()
        if any(host.endswith(h) or host == h for h in _YOUTUBE_HOSTS):
            return False
        if any(host.endswith(h) or host == h for h in _VIMEO_HOSTS):
            return False
        path = (parsed.path or "").lower()
        return path.endswith(_VIDEO_EXTENSIONS)

    def download(self, url: str, job: TranscriptionJob) -> TranscriptionJob:
        if not self.validate_url(url):
            job.mark_failed(f"Invalid direct video URL: {url}")
            raise DirectURLIngestionError(f"Invalid direct video URL: {url}")

        job.status = JobStatus.DOWNLOADING
        job.source_url = url
        job.source_type = SourceType.DIRECT_URL

        job_dir = self.download_dir / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(urlparse(url).path).suffix.lower() or ".mp4"
        target = job_dir / f"video{ext}"

        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as resp:
                resp.raise_for_status()
                with open(target, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=_CHUNK_BYTES):
                        if chunk:
                            f.write(chunk)
        except httpx.HTTPError as e:
            job.mark_failed(f"Direct URL download failed: {e}")
            raise DirectURLIngestionError(f"Direct URL download failed: {e}") from e
        except OSError as e:
            job.mark_failed(f"Disk write failed: {e}")
            raise DirectURLIngestionError(f"Disk write failed: {e}") from e

        if not target.exists() or target.stat().st_size == 0:
            job.mark_failed("Direct URL download produced no file")
            raise DirectURLIngestionError("Direct URL download produced no file")

        job.video_file_path = str(target)
        job.metadata = VideoMetadata(
            title=Path(urlparse(url).path).stem or "remote_video",
            duration_seconds=0.0,
            source_url=url,
            source_type=SourceType.DIRECT_URL,
        )
        return job
```

**Self-check:**

```bash
venv/Scripts/python.exe -c "
from ingestion.url_handler import DirectURLHandler
h = DirectURLHandler(download_dir='./downloads')
assert h.validate_url('https://example.com/video.mp4') is True
assert h.validate_url('https://www.youtube.com/watch?v=abc') is False
assert h.validate_url('https://vimeo.com/12345') is False
assert h.validate_url('https://example.com/page.html') is False
assert h.validate_url('') is False
print('Phase 5b: PASS')
"
```

---

### Step 3 — Backend Phase 5c: VimeoHandler

**File:** `ingestion/vimeo_handler.py`

```python
"""
NTH Transcript Engine — Vimeo Ingestion Handler
Sprint 5 | Owner: Backend Agent

Uses yt-dlp's native Vimeo extractor — same dependency that already ships with
Sprint 1. Public Vimeo videos work out of the box; private/embed-only videos
are surfaced as a clear error.
"""

import re
from pathlib import Path

from models.transcript import (
    JobStatus,
    SourceType,
    TranscriptionJob,
    VideoMetadata,
)


class VimeoIngestionError(Exception):
    """Raised when Vimeo ingestion fails."""


_VIMEO_URL_RE = re.compile(
    r"^(https?://)?(www\.|player\.)?vimeo\.com/(\d+|[\w\-]+/[\w\-]+|video/\d+)"
    r"(/[\w\-]+)?(\?[^\s]*)?$",
    re.IGNORECASE,
)


class VimeoHandler:
    """Downloads Vimeo videos and extracts metadata via yt-dlp."""

    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def validate_url(self, url: str) -> bool:
        if not isinstance(url, str) or not url.strip():
            return False
        return bool(_VIMEO_URL_RE.match(url.strip()))

    def download(self, url: str, job: TranscriptionJob) -> TranscriptionJob:
        if not self.validate_url(url):
            job.mark_failed(f"Invalid Vimeo URL: {url}")
            raise VimeoIngestionError(f"Invalid Vimeo URL: {url}")

        job.status = JobStatus.DOWNLOADING
        job.source_url = url
        job.source_type = SourceType.VIMEO

        job_dir = self.download_dir / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            import yt_dlp
        except ImportError as e:
            job.mark_failed(f"yt-dlp not installed: {e}")
            raise VimeoIngestionError(f"yt-dlp not installed: {e}") from e

        output_template = str(job_dir / "video.%(ext)s")
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise VimeoIngestionError("yt-dlp returned no info for Vimeo URL")
                ext = info.get("ext", "mp4")
                video_path = job_dir / f"video.{ext}"
                if not video_path.exists():
                    candidates = list(job_dir.glob("video.*"))
                    if not candidates:
                        raise VimeoIngestionError(
                            f"Downloaded video file not found in {job_dir}"
                        )
                    video_path = candidates[0]
                job.video_file_path = str(video_path)
                job.metadata = VideoMetadata(
                    title=info.get("title", "Unknown"),
                    duration_seconds=float(info.get("duration", 0) or 0),
                    source_url=info.get("webpage_url", url),
                    source_type=SourceType.VIMEO,
                    uploader=info.get("uploader"),
                    upload_date=info.get("upload_date"),
                    description=info.get("description"),
                    thumbnail_url=info.get("thumbnail"),
                    view_count=info.get("view_count"),
                    language=info.get("language"),
                )
                return job
        except VimeoIngestionError:
            raise
        except Exception as e:
            job.mark_failed(f"Vimeo download failed: {e}")
            raise VimeoIngestionError(f"Vimeo download failed: {e}") from e
```

**Self-check:**

```bash
venv/Scripts/python.exe -c "
from ingestion.vimeo_handler import VimeoHandler
h = VimeoHandler(download_dir='./downloads')
assert h.validate_url('https://vimeo.com/123456') is True
assert h.validate_url('https://player.vimeo.com/video/123456') is True
assert h.validate_url('https://www.youtube.com/watch?v=abc') is False
assert h.validate_url('') is False
print('Phase 5c: PASS')
"
```

---

### Step 4 — Backend Phase 5d: ALLOWLISTED — `api/routes/jobs.py`

Replace the single `_url_validator` line and the body of `submit_job` with auto-detection. Keep every other endpoint and helper untouched.

Add these imports at the top:

```python
from ingestion.local_file_handler import LocalFileHandler
from ingestion.url_handler import DirectURLHandler
from ingestion.vimeo_handler import VimeoHandler
```

Replace `_url_validator = YouTubeHandler.__new__(YouTubeHandler) ...` with stateless detector instances and a dispatch helper:

```python
_yt_validator = YouTubeHandler.__new__(YouTubeHandler)
_vimeo_validator = VimeoHandler.__new__(VimeoHandler)
_url_validator_direct = DirectURLHandler.__new__(DirectURLHandler)
_local_validator = LocalFileHandler.__new__(LocalFileHandler)


def _detect_source_type(source: str) -> Optional[SourceType]:
    """Walk validators in priority order. Return None if no validator accepts."""
    if _yt_validator.validate_url(source):
        return SourceType.YOUTUBE
    if _vimeo_validator.validate_url(source):
        return SourceType.VIMEO
    if _url_validator_direct.validate_url(source):
        return SourceType.DIRECT_URL
    if _local_validator.validate_path(source):
        return SourceType.LOCAL_FILE
    return None
```

Replace the `submit_job` body so the detected source type is used:

```python
@router.post("", response_model=JobStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_job(payload: SubmitJobRequest, request: Request) -> JobStatusResponse:
    detected = _detect_source_type(payload.url)
    if detected is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unrecognized source. Provide a YouTube URL, Vimeo URL, "
                "direct video URL ending in a media extension, or a local file path."
            ),
        )

    try:
        whisper_model = WhisperModel(payload.whisper_model or "base")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown whisper_model: {payload.whisper_model}",
        )

    job = TranscriptionJob(
        source_url=payload.url,
        source_type=detected,
        whisper_model=whisper_model,
        status=JobStatus.PENDING,
    )

    repo = request.app.state.repository
    processor = request.app.state.processor

    repo.save_job(job)
    processor.submit(job)
    return _job_to_response(job)
```

**Self-check:**

```bash
venv/Scripts/python.exe -c "
from api.routes.jobs import _detect_source_type
from models.transcript import SourceType
assert _detect_source_type('https://www.youtube.com/watch?v=abc') == SourceType.YOUTUBE
assert _detect_source_type('https://vimeo.com/123456') == SourceType.VIMEO
assert _detect_source_type('https://example.com/clip.mp4') == SourceType.DIRECT_URL
assert _detect_source_type('not-a-real-input') is None
print('Phase 5d: PASS')
"
```

---

### Step 5 — Backend Phase 5e: ALLOWLISTED — `api/job_processor.py`

Replace the single-handler ingestion stage with a dispatch on `job.source_type`. The audio-extraction and transcription stages are untouched.

Updated imports:

```python
from ingestion.local_file_handler import LocalFileHandler
from ingestion.url_handler import DirectURLHandler
from ingestion.vimeo_handler import VimeoHandler
from ingestion.youtube_handler import YouTubeHandler
from models.transcript import SourceType, TranscriptionJob
```

Updated `__init__`:

```python
def __init__(self, repository: TranscriptRepository, download_dir: str):
    self.repository = repository
    self.download_dir = download_dir
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    self.youtube = YouTubeHandler(download_dir=download_dir)
    self.vimeo = VimeoHandler(download_dir=download_dir)
    self.direct_url = DirectURLHandler(download_dir=download_dir)
    self.local_file = LocalFileHandler(download_dir=download_dir)
```

Updated ingestion stage in `_process` (replace just the `self.youtube.download(...)` line):

```python
if job.source_type is SourceType.YOUTUBE:
    self.youtube.download(job.source_url, job)
elif job.source_type is SourceType.VIMEO:
    self.vimeo.download(job.source_url, job)
elif job.source_type is SourceType.DIRECT_URL:
    self.direct_url.download(job.source_url, job)
elif job.source_type is SourceType.LOCAL_FILE:
    self.local_file.ingest(job.source_url, job)
else:
    raise ValueError(f"Unsupported source_type: {job.source_type}")
```

**Self-check:**

```bash
venv/Scripts/python.exe -c "
from api.job_processor import JobProcessor
from storage.repository import TranscriptRepository
proc = JobProcessor(repository=TranscriptRepository(':memory:'), download_dir='./downloads')
assert hasattr(proc, 'youtube')
assert hasattr(proc, 'vimeo')
assert hasattr(proc, 'direct_url')
assert hasattr(proc, 'local_file')
print('Phase 5e: PASS')
"
```

---

### Step 6 — Frontend Phase 5f: ALLOWLISTED — `ui/panels/job_submission_panel.py`

Update only the `ui.input(...)` call inside `render()`:

```python
self._url_input = ui.input(
    label="Video Source (URL or local file path)",
    placeholder="https://youtube.com/... or C:\\path\\to\\video.mp4",
).classes("w-full")
```

Update only the empty-input notification text:

```python
ui.notify("Please enter a video URL or local file path", type="warning")
```

No other change — polling, status badge, error handling, and all callbacks stay byte-identical to Sprint 4.

**Self-check:**

```bash
venv/Scripts/python.exe -c "
from ui.panels.job_submission_panel import JobSubmissionPanel, status_color
panel = JobSubmissionPanel(api_base='http://localhost:8000')
assert panel.current_job_id is None
assert status_color('complete') is not None
print('Phase 5f: PASS')
"
```

---

### Step 7 — QA Phase 5g: `tests/test_sprint5_multi_source.py`

QA Agent writes the test file. Minimum **14 tests**. The full file is in the QA-Agent appendix at the bottom of this doc.

**Hard-gate tests** (sprint-halting):

1. `test_local_file_validate_existing_mp4`
2. `test_local_file_ingest_copies_to_downloads`
3. `test_api_submit_local_file_path_returns_202`
4. `test_source_type_detection_all_four`

```bash
venv/Scripts/python.exe -m pytest tests/test_sprint5_multi_source.py::test_local_file_validate_existing_mp4 -v
venv/Scripts/python.exe -m pytest tests/test_sprint5_multi_source.py::test_local_file_ingest_copies_to_downloads -v
venv/Scripts/python.exe -m pytest tests/test_sprint5_multi_source.py::test_api_submit_local_file_path_returns_202 -v
venv/Scripts/python.exe -m pytest tests/test_sprint5_multi_source.py::test_source_type_detection_all_four -v
```

Any hard-gate failure → halt → backend fixes → QA re-runs.

---

### Step 8 — QA Gate 2: Full Suite

```bash
venv/Scripts/python.exe -m pytest tests/ -v --tb=long
```

Expected: **59 prior + ≥14 Sprint 5 = ≥73 passing**. Any prior-sprint regression is a critical failure — halt immediately.

---

### Step 9 — Frozen Asset Verification

```bash
git diff --name-only HEAD
```

Must show **only** the four allowlisted files (`api/routes/jobs.py`, `api/job_processor.py`, `ui/panels/job_submission_panel.py`, optional whitespace touches) plus the four new files. Any other change is a sprint failure.

---

### Step 10 — DoD Report

```
DoD Sprint 5 — Final Report
============================================================
[ ] Sprint 1–4 regression: 59 / 59 pass
[ ] ingestion/local_file_handler.py — LocalFileHandler importable
[ ] ingestion/url_handler.py — DirectURLHandler importable
[ ] ingestion/vimeo_handler.py — VimeoHandler importable
[ ] api/routes/jobs.py — _detect_source_type() returns all four enums
[ ] api/job_processor.py — four handlers wired in __init__
[ ] ui/panels/job_submission_panel.py — label and placeholder updated
[ ] tests/test_sprint5_multi_source.py — ≥14 tests
[ ] Hard gate: test_local_file_validate_existing_mp4 PASS
[ ] Hard gate: test_local_file_ingest_copies_to_downloads PASS
[ ] Hard gate: test_api_submit_local_file_path_returns_202 PASS
[ ] Hard gate: test_source_type_detection_all_four PASS
[ ] Full suite: __ / ≥73 pass
[ ] Frozen-asset check: CLEAN (only allowlisted files modified)
============================================================
OVERALL: PASS / FAIL
```

---

### Step 11 — Manual Verification Checklist (operator-facing)

Print this for the user after the suite passes:

```
With the API running (uvicorn api.main:app --reload --port 8000) and the UI running
(python -m ui.app), confirm in the browser:

[ ] Paste a YouTube URL → status badge progresses to "complete" → transcript loads
[ ] Paste a local file path (e.g. C:\Users\you\Videos\clip.mp4) → status badge progresses to "complete" → transcript loads
[ ] Paste a direct video URL ending in .mp4 → status badge progresses to "complete" → transcript loads
[ ] Paste a Vimeo URL of a public video → status badge progresses to "complete" → transcript loads
[ ] Paste garbage text → submission rejected with a 400 and a clear toast message
```

---

### Step 12 — Git Commit (DoD PASS only)

```bash
git add ingestion/local_file_handler.py ingestion/url_handler.py ingestion/vimeo_handler.py \
        api/routes/jobs.py api/job_processor.py ui/panels/job_submission_panel.py \
        tests/test_sprint5_multi_source.py .claude/agents/CLAUDE_MASTER_SPRINT_5.md
git commit -m "sprint5: multi-source ingestion complete"
git push
```

---

## Critical constraints recap

- `models/transcript.py` is frozen forever — never modify.
- Only the four allowlisted prior-sprint files may be edited; all other prior-sprint files including test files are frozen.
- Local file ingestion **never modifies** the operator's source file — copy only.
- Direct URL handler **rejects** YouTube and Vimeo URLs — those are routed to dedicated handlers.
- The API request schema does **not** gain a new field. Source type is auto-detected.
- Backend agent writes zero test code.

---

## QA-Agent Appendix — Full Test File

**File:** `tests/test_sprint5_multi_source.py`

```python
"""
NTH Transcript Engine — Sprint 5 Multi-Source Ingestion Tests
QA Agent | Sprint 5
Tests: 18
Hard Gates: test_local_file_validate_existing_mp4,
            test_local_file_ingest_copies_to_downloads,
            test_api_submit_local_file_path_returns_202,
            test_source_type_detection_all_four
"""

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tmp_downloads(tmp_path):
    d = tmp_path / "downloads"
    d.mkdir()
    return str(d)


@pytest.fixture
def tmp_mp4(tmp_path):
    """A small placeholder mp4 file for path-validation tests (not playable)."""
    p = tmp_path / "sample.mp4"
    p.write_bytes(b"\x00\x00\x00\x18ftypmp42")  # minimal mp4 magic bytes
    return str(p)


@pytest.fixture
def fastapi_client(tmp_downloads, monkeypatch):
    """In-memory FastAPI TestClient with the processor mocked out."""
    monkeypatch.setenv("DB_PATH", ":memory:")
    monkeypatch.setenv("DOWNLOAD_DIR", tmp_downloads)
    from api.main import app
    from api.job_processor import JobProcessor
    from storage.repository import TranscriptRepository

    repo = TranscriptRepository(db_path=":memory:")
    processor = MagicMock(spec=JobProcessor)
    app.state.repository = repo
    app.state.processor = processor

    with TestClient(app) as client:
        yield client, repo, processor


# ============================================================================
# LocalFileHandler — validation
# ============================================================================

def test_local_file_validate_existing_mp4(tmp_downloads, tmp_mp4):
    """HARD GATE: an existing .mp4 file path is accepted."""
    from ingestion.local_file_handler import LocalFileHandler
    handler = LocalFileHandler(download_dir=tmp_downloads)
    assert handler.validate_path(tmp_mp4) is True


def test_local_file_validate_nonexistent_path(tmp_downloads):
    from ingestion.local_file_handler import LocalFileHandler
    handler = LocalFileHandler(download_dir=tmp_downloads)
    assert handler.validate_path("/no/such/file.mp4") is False


def test_local_file_validate_unsupported_extension(tmp_path, tmp_downloads):
    from ingestion.local_file_handler import LocalFileHandler
    p = tmp_path / "doc.txt"
    p.write_text("not a video")
    handler = LocalFileHandler(download_dir=tmp_downloads)
    assert handler.validate_path(str(p)) is False


def test_local_file_validate_empty_string(tmp_downloads):
    from ingestion.local_file_handler import LocalFileHandler
    handler = LocalFileHandler(download_dir=tmp_downloads)
    assert handler.validate_path("") is False


# ============================================================================
# LocalFileHandler — ingest
# ============================================================================

def test_local_file_ingest_copies_to_downloads(tmp_downloads, tmp_mp4):
    """HARD GATE: ingest copies source into downloads/{job_id}/ and sets video_file_path."""
    from ingestion.local_file_handler import LocalFileHandler
    from models.transcript import TranscriptionJob, SourceType

    handler = LocalFileHandler(download_dir=tmp_downloads)
    job = TranscriptionJob()
    handler.ingest(tmp_mp4, job)

    assert job.source_type is SourceType.LOCAL_FILE
    assert job.video_file_path is not None
    assert Path(job.video_file_path).exists()
    assert Path(job.video_file_path).parent.name == job.job_id
    # source file must be untouched
    assert Path(tmp_mp4).exists()


def test_local_file_ingest_invalid_path_raises(tmp_downloads):
    from ingestion.local_file_handler import (
        LocalFileHandler,
        LocalFileIngestionError,
    )
    from models.transcript import TranscriptionJob, JobStatus

    handler = LocalFileHandler(download_dir=tmp_downloads)
    job = TranscriptionJob()
    with pytest.raises(LocalFileIngestionError):
        handler.ingest("/no/such/file.mp4", job)
    assert job.status is JobStatus.FAILED


# ============================================================================
# DirectURLHandler — validation
# ============================================================================

def test_direct_url_validate_video_url(tmp_downloads):
    from ingestion.url_handler import DirectURLHandler
    h = DirectURLHandler(download_dir=tmp_downloads)
    assert h.validate_url("https://example.com/clip.mp4") is True
    assert h.validate_url("http://cdn.example.org/path/to/movie.webm") is True


def test_direct_url_validate_rejects_youtube_and_vimeo(tmp_downloads):
    from ingestion.url_handler import DirectURLHandler
    h = DirectURLHandler(download_dir=tmp_downloads)
    assert h.validate_url("https://www.youtube.com/watch?v=abc") is False
    assert h.validate_url("https://youtu.be/abc") is False
    assert h.validate_url("https://vimeo.com/123456") is False


def test_direct_url_validate_rejects_html_and_empty(tmp_downloads):
    from ingestion.url_handler import DirectURLHandler
    h = DirectURLHandler(download_dir=tmp_downloads)
    assert h.validate_url("https://example.com/page.html") is False
    assert h.validate_url("") is False
    assert h.validate_url("ftp://example.com/clip.mp4") is False


def test_direct_url_download_streams_to_disk(tmp_downloads):
    """Mocked httpx.stream — ensures bytes are written to disk and metadata populated."""
    from ingestion.url_handler import DirectURLHandler
    from models.transcript import TranscriptionJob, SourceType

    handler = DirectURLHandler(download_dir=tmp_downloads)
    job = TranscriptionJob()
    url = "https://example.com/clip.mp4"

    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.iter_bytes = MagicMock(return_value=[b"chunk1", b"chunk2"])
    fake_ctx = MagicMock()
    fake_ctx.__enter__ = MagicMock(return_value=fake_resp)
    fake_ctx.__exit__ = MagicMock(return_value=False)

    with patch("ingestion.url_handler.httpx.stream", return_value=fake_ctx):
        handler.download(url, job)

    assert job.source_type is SourceType.DIRECT_URL
    assert job.video_file_path is not None
    assert Path(job.video_file_path).read_bytes() == b"chunk1chunk2"


# ============================================================================
# VimeoHandler — validation
# ============================================================================

def test_vimeo_validate_url(tmp_downloads):
    from ingestion.vimeo_handler import VimeoHandler
    h = VimeoHandler(download_dir=tmp_downloads)
    assert h.validate_url("https://vimeo.com/123456") is True
    assert h.validate_url("https://www.vimeo.com/123456") is True
    assert h.validate_url("https://player.vimeo.com/video/123456") is True


def test_vimeo_validate_rejects_other(tmp_downloads):
    from ingestion.vimeo_handler import VimeoHandler
    h = VimeoHandler(download_dir=tmp_downloads)
    assert h.validate_url("https://www.youtube.com/watch?v=abc") is False
    assert h.validate_url("https://example.com/clip.mp4") is False
    assert h.validate_url("") is False


# ============================================================================
# Source-type detection (the API-layer dispatcher)
# ============================================================================

def test_source_type_detection_all_four(tmp_mp4):
    """HARD GATE: detector returns the correct enum for every supported source."""
    from api.routes.jobs import _detect_source_type
    from models.transcript import SourceType

    assert _detect_source_type("https://www.youtube.com/watch?v=abc") == SourceType.YOUTUBE
    assert _detect_source_type("https://vimeo.com/123456") == SourceType.VIMEO
    assert _detect_source_type("https://example.com/clip.mp4") == SourceType.DIRECT_URL
    assert _detect_source_type(tmp_mp4) == SourceType.LOCAL_FILE
    assert _detect_source_type("not-a-real-input") is None


# ============================================================================
# API integration
# ============================================================================

def test_api_submit_local_file_path_returns_202(fastapi_client, tmp_mp4):
    """HARD GATE: POST /jobs with a local file path returns 202 and queues the job."""
    client, repo, processor = fastapi_client
    response = client.post("/jobs", json={"url": tmp_mp4, "whisper_model": "base"})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["source_url"] == tmp_mp4
    processor.submit.assert_called_once()


def test_api_submit_direct_url_returns_202(fastapi_client):
    client, repo, processor = fastapi_client
    response = client.post(
        "/jobs",
        json={"url": "https://example.com/clip.mp4", "whisper_model": "base"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "pending"


def test_api_submit_vimeo_url_returns_202(fastapi_client):
    client, repo, processor = fastapi_client
    response = client.post(
        "/jobs",
        json={"url": "https://vimeo.com/123456", "whisper_model": "base"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "pending"


def test_api_submit_garbage_returns_400(fastapi_client):
    client, repo, processor = fastapi_client
    response = client.post(
        "/jobs",
        json={"url": "this is not a url or a path", "whisper_model": "base"},
    )
    assert response.status_code == 400
    assert "Unrecognized source" in response.json()["detail"]


# ============================================================================
# Regression
# ============================================================================

def test_sprint1_2_3_4_regression():
    """Imports from prior sprints remain clean."""
    from models.transcript import (
        Transcript, TranscriptionJob, TranscriptSegment,
        VideoMetadata, SourceType, JobStatus, WhisperModel,
    )
    from ingestion.youtube_handler import YouTubeHandler
    from transcription.engine import TranscriptionEngine
    from transcription.audio_extractor import AudioExtractor
    from storage.repository import TranscriptRepository
    from api.main import app
    from api.routes.jobs import router as jobs_router
    from api.routes.exports import router as exports_router
    from exports.txt_exporter import export_txt
    from exports.srt_exporter import export_srt
    from exports.json_exporter import export_json
    from exports.docx_exporter import export_docx
    assert True
```

---

## End of CLAUDE_MASTER_SPRINT_5.md
