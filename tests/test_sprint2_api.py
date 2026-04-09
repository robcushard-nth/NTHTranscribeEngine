"""
NTH Transcript Engine — Sprint 2 API Tests
Owner: QA Agent
"""

import threading
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.job_processor import JobProcessor
from api.main import app
from models.transcript import (
    JobStatus,
    SourceType,
    Transcript,
    TranscriptionJob,
    TranscriptSegment,
    VideoMetadata,
    WhisperModel,
)
from storage.repository import TranscriptRepository


# ------------------------------- fixtures ------------------------------------

@pytest.fixture
def repo(tmp_path):
    return TranscriptRepository(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def sample_job():
    return TranscriptionJob(
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        source_type=SourceType.YOUTUBE,
        whisper_model=WhisperModel.BASE,
        status=JobStatus.PENDING,
    )


@pytest.fixture
def sample_transcript(sample_job):
    segs = [
        TranscriptSegment(0, 0.0, 1.5, "hello"),
        TranscriptSegment(1, 1.5, 3.0, "world", confidence=-0.2),
    ]
    return Transcript(
        job_id=sample_job.job_id,
        segments=segs,
        full_text="hello world",
        language_detected="en",
        whisper_model_used="base",
        processing_duration_seconds=1.23,
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with stubbed processor (no real downloads/transcription)."""
    db = tmp_path / "api_test.db"
    dl = tmp_path / "downloads"
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("DOWNLOAD_DIR", str(dl))

    # Patch JobProcessor.submit to no-op so tests don't spawn real threads.
    with patch.object(JobProcessor, "submit", lambda self, job: None):
        with TestClient(app) as c:
            yield c


# ----------------------------- repository tests ------------------------------

def test_repository_save_and_get_job(repo, sample_job):
    repo.save_job(sample_job)
    fetched = repo.get_job(sample_job.job_id)
    assert fetched is not None
    assert fetched.job_id == sample_job.job_id
    assert fetched.source_url == sample_job.source_url
    assert fetched.status is JobStatus.PENDING
    assert fetched.whisper_model is WhisperModel.BASE


def test_repository_update_job_status(repo, sample_job):
    repo.save_job(sample_job)
    sample_job.status = JobStatus.TRANSCRIBING
    repo.update_job(sample_job)
    fetched = repo.get_job(sample_job.job_id)
    assert fetched.status is JobStatus.TRANSCRIBING


def test_repository_get_job_not_found(repo):
    assert repo.get_job("nonexistent-id") is None


def test_repository_save_and_get_transcript(repo, sample_job, sample_transcript):
    repo.save_job(sample_job)
    repo.save_transcript(sample_transcript)
    fetched = repo.get_transcript_by_job_id(sample_job.job_id)
    assert fetched is not None
    assert fetched.job_id == sample_job.job_id
    assert fetched.full_text == "hello world"
    assert fetched.language_detected == "en"


def test_repository_list_jobs(repo):
    j1 = TranscriptionJob(source_url="https://youtube.com/watch?v=a")
    j2 = TranscriptionJob(source_url="https://youtube.com/watch?v=b")
    repo.save_job(j1)
    repo.save_job(j2)
    jobs = repo.list_jobs()
    ids = {j.job_id for j in jobs}
    assert j1.job_id in ids
    assert j2.job_id in ids
    assert len(jobs) >= 2


def test_repository_transcript_segments_persist(repo, sample_job, sample_transcript):
    repo.save_job(sample_job)
    repo.save_transcript(sample_transcript)
    fetched = repo.get_transcript_by_job_id(sample_job.job_id)
    assert fetched.segment_count == 2
    assert fetched.segments[0].text == "hello"
    assert fetched.segments[1].text == "world"
    assert fetched.segments[1].confidence == pytest.approx(-0.2)
    assert fetched.segments[0].start_time == 0.0
    assert fetched.segments[1].end_time == 3.0


def test_repository_thread_safety(repo):
    errors = []

    def writer(i):
        try:
            for k in range(10):
                j = TranscriptionJob(source_url=f"https://youtube.com/watch?v=t{i}_{k}")
                repo.save_job(j)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(repo.list_jobs()) >= 50


# -------------------------------- API tests ----------------------------------

def test_api_submit_job_valid_url(client):
    resp = client.post(
        "/jobs",
        json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "whisper_model": "base",
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "job_id" in body
    assert body["status"] == "pending"
    assert body["whisper_model"] == "base"


def test_api_submit_job_invalid_url(client):
    resp = client.post(
        "/jobs",
        json={"url": "not a url", "whisper_model": "base"},
    )
    assert resp.status_code == 400


def test_api_get_job_status(client):
    submit = client.post(
        "/jobs",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    job_id = submit.json()["job_id"]
    resp = client.get(f"/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["job_id"] == job_id


def test_api_get_job_not_found(client):
    resp = client.get("/jobs/does-not-exist")
    assert resp.status_code == 404


def test_api_get_transcript_not_complete(client):
    submit = client.post(
        "/jobs",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    job_id = submit.json()["job_id"]
    resp = client.get(f"/jobs/{job_id}/transcript")
    assert resp.status_code == 409


def test_api_get_transcript_complete(client):
    # Submit a job, then directly mark it complete + insert a transcript
    submit = client.post(
        "/jobs",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    job_id = submit.json()["job_id"]

    repo = client.app.state.repository
    job = repo.get_job(job_id)
    job.mark_complete()
    repo.update_job(job)

    transcript = Transcript(
        job_id=job_id,
        segments=[
            TranscriptSegment(0, 0.0, 2.0, "hello"),
            TranscriptSegment(1, 2.0, 4.0, "world"),
        ],
        full_text="hello world",
        language_detected="en",
        whisper_model_used="base",
        processing_duration_seconds=0.5,
    )
    repo.save_transcript(transcript)

    resp = client.get(f"/jobs/{job_id}/transcript")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == job_id
    assert body["full_text"] == "hello world"
    assert body["segment_count"] == 2
    assert body["word_count"] == 2
    assert len(body["segments"]) == 2
    assert body["segments"][0]["formatted_start"] == "00:00:00"


def test_api_list_jobs(client):
    client.post("/jobs", json={"url": "https://www.youtube.com/watch?v=aaa1111"})
    client.post("/jobs", json={"url": "https://www.youtube.com/watch?v=bbb2222"})
    resp = client.get("/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2


# --------------------------- Sprint 1 regression -----------------------------

def test_sprint1_regression():
    """Sprint 1 model imports must remain clean."""
    from models.transcript import (  # noqa: F401
        JobStatus,
        SourceType,
        Transcript,
        TranscriptionJob,
        TranscriptSegment,
        VideoMetadata,
        WhisperModel,
    )
    from ingestion.youtube_handler import YouTubeHandler, VideoIngestionError  # noqa: F401
    from transcription.audio_extractor import AudioExtractor, FFmpegNotFoundError  # noqa: F401
    from transcription.engine import TranscriptionEngine, TranscriptionError  # noqa: F401
    assert TranscriptionJob().status is JobStatus.PENDING
