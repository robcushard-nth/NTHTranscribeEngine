# QA Agent — NTH Transcript Engine Sprint 2

## Role
You write all Sprint 2 tests. Backend agent writes zero test code.
You run all gates, validate frozen assets, report DoD to PM Agent.

Read `CLAUDE_MASTER_SPRINT_2.md` before writing tests.

---

## Frozen Asset Verification
```bash
git diff --name-only HEAD
```
Must show ZERO modifications to: `models/transcript.py`, `ingestion/`, `transcription/`,
`tests/test_sprint1_foundation.py`. Only `requirements.txt` and new Sprint 2 files permitted.

---

## QA Gate 1 — Hard Gate Tests
```bash
pytest tests/test_sprint2_api.py::test_repository_save_and_get_job -v
pytest tests/test_sprint2_api.py::test_api_submit_job_valid_url -v
pytest tests/test_sprint2_api.py::test_api_get_transcript_complete -v
```
Sprint halts on any failure.

---

## QA Gate 2 — Full Suite
```bash
pytest tests/ -v --tb=long
```
Expected: 30 tests (15 Sprint 1 + 15 Sprint 2). Minimum 29.
Any Sprint 1 regression is a critical failure.

---

## Full Test File — Copy-Paste Ready

**File:** `tests/test_sprint2_api.py`

```python
"""
NTH Transcript Engine — Sprint 2 API Tests
QA Agent | Sprint 2
Tests: 15
Hard Gates: test_repository_save_and_get_job, test_api_submit_job_valid_url,
            test_api_get_transcript_complete
"""

import pytest
import json
import threading
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ===========================================================================
# FIXTURES
# ===========================================================================

@pytest.fixture
def repo():
    """In-memory repository for isolation."""
    from storage.repository import TranscriptRepository
    return TranscriptRepository(db_path=":memory:")


@pytest.fixture
def sample_job():
    from models.transcript import TranscriptionJob, SourceType, WhisperModel
    return TranscriptionJob(
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        source_type=SourceType.YOUTUBE,
        whisper_model=WhisperModel.BASE
    )


@pytest.fixture
def sample_transcript(sample_job):
    from models.transcript import Transcript, TranscriptSegment, VideoMetadata, SourceType
    meta = VideoMetadata(
        title="Test Video",
        duration_seconds=212.0,
        source_url=sample_job.source_url,
        source_type=SourceType.YOUTUBE,
        uploader="TestChannel"
    )
    segs = [
        TranscriptSegment(segment_id=0, start_time=0.0, end_time=5.0, text="Hello world"),
        TranscriptSegment(segment_id=1, start_time=5.0, end_time=10.0, text="This is a test"),
    ]
    return Transcript(
        job_id=sample_job.job_id,
        metadata=meta,
        segments=segs,
        full_text="Hello world This is a test",
        language_detected="en",
        whisper_model_used="base",
        processing_duration_seconds=12.5
    )


@pytest.fixture
def test_client():
    """FastAPI test client with in-memory dependencies."""
    from api.main import app
    from storage.repository import TranscriptRepository
    from api.job_processor import JobProcessor

    repo = TranscriptRepository(db_path=":memory:")
    processor = MagicMock(spec=JobProcessor)

    app.state.repository = repo
    app.state.processor = processor
    with TestClient(app) as client:
        yield client, repo, processor


# ===========================================================================
# REPOSITORY TESTS
# ===========================================================================

def test_repository_save_and_get_job(repo, sample_job):
    """HARD GATE: save_job then get_job returns same job."""
    repo.save_job(sample_job)
    retrieved = repo.get_job(sample_job.job_id)
    assert retrieved is not None
    assert retrieved.job_id == sample_job.job_id
    assert retrieved.source_url == sample_job.source_url


def test_repository_update_job_status(repo, sample_job):
    """update_job persists status change correctly."""
    from models.transcript import JobStatus
    repo.save_job(sample_job)
    sample_job.mark_complete()
    repo.update_job(sample_job)
    updated = repo.get_job(sample_job.job_id)
    assert updated.status == JobStatus.COMPLETE
    assert updated.completed_at is not None


def test_repository_get_job_not_found(repo):
    """get_job returns None for unknown job_id."""
    result = repo.get_job("00000000-0000-0000-0000-000000000000")
    assert result is None


def test_repository_save_and_get_transcript(repo, sample_job, sample_transcript):
    """save_transcript then get_transcript_by_job_id returns transcript."""
    repo.save_job(sample_job)
    repo.save_transcript(sample_transcript)
    retrieved = repo.get_transcript_by_job_id(sample_job.job_id)
    assert retrieved is not None
    assert retrieved.job_id == sample_job.job_id
    assert retrieved.full_text == "Hello world This is a test"


def test_repository_list_jobs(repo):
    """list_jobs returns all saved jobs."""
    from models.transcript import TranscriptionJob
    jobs = [
        TranscriptionJob(source_url=f"https://youtube.com/watch?v=test{i}")
        for i in range(3)
    ]
    for j in jobs:
        repo.save_job(j)
    result = repo.list_jobs()
    assert len(result) == 3


def test_repository_transcript_segments_persist(repo, sample_job, sample_transcript):
    """Segments serialize and deserialize correctly through JSON."""
    repo.save_job(sample_job)
    repo.save_transcript(sample_transcript)
    retrieved = repo.get_transcript_by_job_id(sample_job.job_id)
    assert retrieved.segment_count == 2
    assert retrieved.segments[0].text == "Hello world"
    assert retrieved.segments[1].start_time == 5.0
    assert retrieved.segments[0].formatted_start == "00:00:00"


def test_repository_thread_safety(repo):
    """Concurrent writes do not corrupt job data."""
    from models.transcript import TranscriptionJob
    import uuid

    errors = []
    jobs_created = []

    def write_job():
        try:
            job = TranscriptionJob(source_url=f"https://youtube.com/watch?v={uuid.uuid4()}")
            repo.save_job(job)
            jobs_created.append(job.job_id)
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=write_job) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Thread safety errors: {errors}"
    assert len(repo.list_jobs()) == 10


# ===========================================================================
# API TESTS
# ===========================================================================

def test_api_submit_job_valid_url(test_client):
    """HARD GATE: POST /jobs with valid YouTube URL returns 202."""
    client, repo, processor = test_client
    response = client.post("/jobs/", json={
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "whisper_model": "base"
    })
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    assert data["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    processor.submit.assert_called_once()


def test_api_submit_job_invalid_url(test_client):
    """POST /jobs with invalid URL returns 400."""
    client, repo, processor = test_client
    response = client.post("/jobs/", json={
        "url": "https://vimeo.com/123456",
        "whisper_model": "base"
    })
    assert response.status_code == 400
    assert "Invalid" in response.json()["detail"]


def test_api_get_job_status(test_client, sample_job):
    """GET /jobs/{id} returns correct status for known job."""
    client, repo, processor = test_client
    repo.save_job(sample_job)
    response = client.get(f"/jobs/{sample_job.job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == sample_job.job_id
    assert data["status"] == "pending"


def test_api_get_job_not_found(test_client):
    """GET /jobs/{id} returns 404 for unknown job_id."""
    client, repo, processor = test_client
    response = client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_api_get_transcript_not_complete(test_client, sample_job):
    """GET /jobs/{id}/transcript returns 409 if job is not COMPLETE."""
    client, repo, processor = test_client
    repo.save_job(sample_job)
    response = client.get(f"/jobs/{sample_job.job_id}/transcript")
    assert response.status_code == 409
    assert "not complete" in response.json()["detail"].lower()


def test_api_get_transcript_complete(test_client, sample_job, sample_transcript):
    """HARD GATE: GET /jobs/{id}/transcript returns TranscriptResponse when COMPLETE."""
    client, repo, processor = test_client
    sample_job.mark_complete()
    repo.save_job(sample_job)
    repo.save_transcript(sample_transcript)
    response = client.get(f"/jobs/{sample_job.job_id}/transcript")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == sample_job.job_id
    assert data["full_text"] == "Hello world This is a test"
    assert data["segment_count"] == 2
    assert data["word_count"] == 6
    assert len(data["segments"]) == 2


def test_api_list_jobs(test_client):
    """GET /jobs returns a list of job summaries."""
    from models.transcript import TranscriptionJob
    client, repo, processor = test_client
    for i in range(3):
        j = TranscriptionJob(source_url=f"https://youtube.com/watch?v=test{i}")
        repo.save_job(j)
    response = client.get("/jobs/")
    assert response.status_code == 200
    assert len(response.json()) == 3


# ===========================================================================
# REGRESSION
# ===========================================================================

def test_sprint1_regression():
    """Sprint 1 model imports remain clean after Sprint 2."""
    from models.transcript import (
        Transcript, TranscriptionJob, TranscriptSegment,
        VideoMetadata, SourceType, JobStatus, WhisperModel
    )
    from ingestion.youtube_handler import YouTubeHandler
    from transcription.engine import TranscriptionEngine
    assert True  # Import success is the assertion
```

---

## Full Test Run Command
```bash
pytest tests/ -v --tb=long 2>&1
```

Expected:
```
tests/test_sprint1_foundation.py: 15 passed
tests/test_sprint2_api.py: 15 passed
30 passed in X.Xs
```

---

## DoD Checklist — QA Report to PM Agent
```
DoD Sprint 2 — QA Agent Final Report
============================================================
[ ] Sprint 1 regression: 15/15 pass
[ ] storage/repository.py — importable, tables verified
[ ] api/main.py — FastAPI app importable
[ ] api/job_processor.py — JobProcessor importable
[ ] api/routes/jobs.py — 4 endpoints registered
[ ] api/middleware/cors.py — configure_cors importable
[ ] requirements.txt — 4 new deps installed
[ ] tests/test_sprint2_api.py — 15 tests delivered
[ ] Sprint 2 tests: __ / 15 pass
[ ] Hard gate: test_repository_save_and_get_job — PASS / FAIL
[ ] Hard gate: test_api_submit_job_valid_url — PASS / FAIL
[ ] Hard gate: test_api_get_transcript_complete — PASS / FAIL
[ ] Full suite: __ / 30 pass
[ ] Frozen asset check: CLEAN
============================================================
OVERALL: PASS / FAIL
```

---

## Git Commit
```bash
git add -A
git commit -m "sprint2: api layer complete"
```

---

## 🏁 Sprint 2 Milestone Statement

Sprint 2 delivers a fully operational REST API for the NTH Transcript Engine.
The repository layer persists jobs and transcripts with thread-safe SQLite.
The background processor runs the full pipeline without blocking the API.
Four endpoints are live and tested. 30 total tests pass at 100%.

The platform is ready for Sprint 3: NiceGUI Dashboard — a browser-based operator
interface with URL submission, live status polling, and full transcript display.
