"""
NTH Transcript Engine — Sprint 4 Tests (Export Engine + History Panel)
Owner: QA Agent
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.job_processor import JobProcessor
from api.main import app
from exports.docx_exporter import export_docx
from exports.json_exporter import export_json
from exports.srt_exporter import _format_srt_timestamp, export_srt
from exports.txt_exporter import export_txt
from models.transcript import (
    JobStatus,
    SourceType,
    Transcript,
    TranscriptionJob,
    TranscriptSegment,
    WhisperModel,
)
from ui.panels.history_panel import HistoryPanel


# ------------------------------- fixtures ------------------------------------

@pytest.fixture
def sample_transcript():
    segs = [
        TranscriptSegment(0, 0.0, 2.5, "Hello world", confidence=-0.1),
        TranscriptSegment(1, 2.5, 5.123, "Second segment text", confidence=-0.2),
        TranscriptSegment(2, 5.123, 8.0, "Third one", confidence=None),
    ]
    return Transcript(
        job_id="job-abc",
        segments=segs,
        full_text="Hello world Second segment text Third one",
        language_detected="en",
        whisper_model_used="base",
        processing_duration_seconds=1.23,
    )


@pytest.fixture
def client(tmp_path, monkeypatch, sample_transcript):
    db = tmp_path / "exports_api.db"
    dl = tmp_path / "downloads"
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("DOWNLOAD_DIR", str(dl))

    with patch.object(JobProcessor, "submit", lambda self, job: None):
        with TestClient(app) as c:
            yield c


def _seed_complete_job(client, transcript: Transcript) -> str:
    """Submit a job, mark it complete in the repo, save the transcript, return job_id."""
    submit = client.post(
        "/jobs",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    assert submit.status_code == 202
    job_id = submit.json()["job_id"]
    repo = client.app.state.repository
    job = repo.get_job(job_id)
    job.mark_complete()
    repo.update_job(job)
    transcript.job_id = job_id
    repo.save_transcript(transcript)
    return job_id


# --------------------------------- TXT ---------------------------------------

def test_export_txt_basic(sample_transcript):
    out = export_txt(sample_transcript)
    lines = out.strip().split("\n")
    seg_lines = [l for l in lines if l.startswith("[")]
    assert len(seg_lines) == 3
    assert seg_lines[0].startswith("[00:00:00] ")
    assert "Hello world" in seg_lines[0]


def test_export_txt_word_count_header(sample_transcript):
    out = export_txt(sample_transcript)
    assert f"# Words: {sample_transcript.word_count}" in out
    assert "# Transcript " in out


# --------------------------------- SRT ---------------------------------------

def test_export_srt_format(sample_transcript):
    out = export_srt(sample_transcript)
    assert out.startswith("1\n00:00:00,000 --> ")


def test_export_srt_indexing(sample_transcript):
    out = export_srt(sample_transcript)
    blocks = [b for b in out.split("\n\n") if b.strip()]
    indices = [int(b.splitlines()[0]) for b in blocks]
    assert indices == [1, 2, 3]


def test_export_srt_millisecond_precision():
    # 5.123 seconds → 00:00:05,123
    assert _format_srt_timestamp(5.123) == "00:00:05,123"
    # 3661.5 seconds → 01:01:01,500
    assert _format_srt_timestamp(3661.5) == "01:01:01,500"
    # 0.001 seconds → 00:00:00,001
    assert _format_srt_timestamp(0.001) == "00:00:00,001"


# --------------------------------- JSON --------------------------------------

def test_export_json_round_trip(sample_transcript):
    raw = export_json(sample_transcript)
    parsed = json.loads(raw)
    expected_keys = {
        "transcript_id",
        "job_id",
        "full_text",
        "language_detected",
        "whisper_model_used",
        "segment_count",
        "word_count",
        "processing_duration_seconds",
        "created_at",
        "segments",
    }
    assert expected_keys.issubset(parsed.keys())
    assert parsed["segment_count"] == 3
    assert parsed["language_detected"] == "en"


def test_export_json_segments_complete(sample_transcript):
    parsed = json.loads(export_json(sample_transcript))
    assert len(parsed["segments"]) == 3
    seg0 = parsed["segments"][0]
    for key in (
        "segment_id",
        "start_time",
        "end_time",
        "formatted_start",
        "formatted_end",
        "text",
        "confidence",
    ):
        assert key in seg0
    assert seg0["confidence"] == pytest.approx(-0.1)


# --------------------------------- DOCX --------------------------------------

def test_export_docx_returns_bytes(sample_transcript):
    body = export_docx(sample_transcript)
    assert isinstance(body, bytes)
    assert len(body) > 0
    # .docx files are zip archives → start with PK
    assert body[:2] == b"PK"


# --------------------------------- API ---------------------------------------

def test_api_export_txt(client, sample_transcript):
    job_id = _seed_complete_job(client, sample_transcript)
    resp = client.get(f"/jobs/{job_id}/transcript/export", params={"format": "txt"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert b"[00:00:00]" in resp.content


def test_api_export_srt(client, sample_transcript):
    job_id = _seed_complete_job(client, sample_transcript)
    resp = client.get(f"/jobs/{job_id}/transcript/export", params={"format": "srt"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/x-subrip")
    assert resp.content.startswith(b"1\n00:00:00,000 --> ")


def test_api_export_json(client, sample_transcript):
    job_id = _seed_complete_job(client, sample_transcript)
    resp = client.get(f"/jobs/{job_id}/transcript/export", params={"format": "json"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    parsed = json.loads(resp.content)
    assert parsed["job_id"] == job_id


def test_api_export_docx(client, sample_transcript):
    job_id = _seed_complete_job(client, sample_transcript)
    resp = client.get(f"/jobs/{job_id}/transcript/export", params={"format": "docx"})
    assert resp.status_code == 200
    assert "wordprocessingml.document" in resp.headers["content-type"]
    assert resp.content[:2] == b"PK"
    assert "attachment" in resp.headers.get("content-disposition", "")


def test_api_export_invalid_format(client, sample_transcript):
    job_id = _seed_complete_job(client, sample_transcript)
    resp = client.get(f"/jobs/{job_id}/transcript/export", params={"format": "pdf"})
    assert resp.status_code == 400


def test_api_export_not_complete(client):
    submit = client.post(
        "/jobs",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    job_id = submit.json()["job_id"]
    resp = client.get(f"/jobs/{job_id}/transcript/export", params={"format": "txt"})
    assert resp.status_code == 409


def test_api_export_job_not_found(client):
    resp = client.get("/jobs/does-not-exist/transcript/export", params={"format": "txt"})
    assert resp.status_code == 404


# ----------------------------- HistoryPanel ----------------------------------

def test_history_panel_init():
    panel = HistoryPanel(api_base="http://localhost:8000")
    assert panel.api_base == "http://localhost:8000"
    assert panel._jobs == []
    assert panel.on_select is None


@pytest.mark.asyncio
async def test_history_panel_refresh_calls_api():
    panel = HistoryPanel(api_base="http://localhost:8000")

    fake_jobs = [
        {
            "job_id": "abc12345-deadbeef",
            "status": "complete",
            "source_url": "https://www.youtube.com/watch?v=xxx",
            "whisper_model": "base",
            "created_at": "2026-04-09T10:00:00",
        }
    ]

    class FakeResp:
        status_code = 200
        def json(self):
            return fake_jobs

    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def get(self, url):
            FakeClient.last_url = url
            return FakeResp()

    with patch(
        "ui.panels.history_panel.httpx.AsyncClient", return_value=FakeClient()
    ):
        # _rebuild_list touches NiceGUI elements; stub it out for this unit test
        with patch.object(HistoryPanel, "_rebuild_list", lambda self: None):
            await panel.refresh()

    assert panel._jobs == fake_jobs
    assert FakeClient.last_url.endswith("/jobs")


# --------------------------- prior-sprint regression -------------------------

def test_sprint1_2_3_regression():
    from models.transcript import TranscriptionJob, JobStatus  # noqa: F401
    from ingestion.youtube_handler import YouTubeHandler  # noqa: F401
    from transcription.engine import TranscriptionEngine  # noqa: F401
    from storage.repository import TranscriptRepository  # noqa: F401
    from api.routes.jobs import router as jobs_router  # noqa: F401
    from api.routes.exports import router as exports_router  # noqa: F401
    from ui.colors import NTH_DARK_BG  # noqa: F401
    from ui.panels.job_submission_panel import JobSubmissionPanel  # noqa: F401
    from ui.panels.transcript_viewer_panel import TranscriptViewerPanel  # noqa: F401
    from ui.panels.history_panel import HistoryPanel  # noqa: F401
    assert TranscriptionJob().status is JobStatus.PENDING
