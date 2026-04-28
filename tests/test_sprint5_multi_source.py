"""
NTH Transcript Engine — Sprint 5 Multi-Source Ingestion Tests
QA Agent | Sprint 5
Tests: 18
Hard Gates:
  - test_local_file_validate_existing_mp4
  - test_local_file_ingest_copies_to_downloads
  - test_api_submit_local_file_path_returns_202
  - test_source_type_detection_all_four
"""

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
    p = tmp_path / "sample.mp4"
    p.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    return str(p)


@pytest.fixture
def fastapi_client(tmp_path, monkeypatch):
    """TestClient with JobProcessor.submit patched to record calls."""
    from api.job_processor import JobProcessor
    from api.main import app

    db = tmp_path / "api_test.db"
    dl = tmp_path / "downloads"
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("DOWNLOAD_DIR", str(dl))

    submitted = []
    with patch.object(JobProcessor, "submit", lambda self, job: submitted.append(job)):
        with TestClient(app) as client:
            yield client, client.app.state.repository, submitted


# ============================================================================
# LocalFileHandler — validation
# ============================================================================

def test_local_file_validate_existing_mp4(tmp_downloads, tmp_mp4):
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


def test_local_file_validate_strips_windows_bidi_mark(tmp_downloads, tmp_mp4):
    """Windows File Explorer 'Copy as path' prepends U+202A; validator must tolerate it."""
    from ingestion.local_file_handler import LocalFileHandler
    handler = LocalFileHandler(download_dir=tmp_downloads)
    assert handler.validate_path("‪" + tmp_mp4) is True
    assert handler.validate_path('"' + tmp_mp4 + '"') is True  # quoted path


# ============================================================================
# LocalFileHandler — ingest
# ============================================================================

def test_local_file_ingest_copies_to_downloads(tmp_downloads, tmp_mp4):
    from ingestion.local_file_handler import LocalFileHandler
    from models.transcript import TranscriptionJob, SourceType

    handler = LocalFileHandler(download_dir=tmp_downloads)
    job = TranscriptionJob()
    handler.ingest(tmp_mp4, job)

    assert job.source_type is SourceType.LOCAL_FILE
    assert job.video_file_path is not None
    target = Path(job.video_file_path)
    assert target.exists()
    assert target.parent.name == job.job_id
    assert Path(tmp_mp4).exists(), "source file must not be deleted"


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
    assert h.validate_url("http://cdn.example.org/path/movie.webm") is True


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
    from models.transcript import SourceType
    client, repo, submitted = fastapi_client
    response = client.post("/jobs", json={"url": tmp_mp4, "whisper_model": "base"})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["source_url"] == tmp_mp4
    assert len(submitted) == 1
    assert submitted[0].source_type is SourceType.LOCAL_FILE


def test_api_submit_direct_url_returns_202(fastapi_client):
    from models.transcript import SourceType
    client, repo, submitted = fastapi_client
    response = client.post(
        "/jobs",
        json={"url": "https://example.com/clip.mp4", "whisper_model": "base"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    assert submitted[-1].source_type is SourceType.DIRECT_URL


def test_api_submit_vimeo_url_returns_202(fastapi_client):
    from models.transcript import SourceType
    client, repo, submitted = fastapi_client
    response = client.post(
        "/jobs",
        json={"url": "https://vimeo.com/123456", "whisper_model": "base"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    assert submitted[-1].source_type is SourceType.VIMEO


def test_api_submit_garbage_returns_400(fastapi_client):
    client, repo, submitted = fastapi_client
    response = client.post(
        "/jobs",
        json={"url": "this is not a url or a path", "whisper_model": "base"},
    )
    assert response.status_code == 400
    assert "Unrecognized source" in response.json()["detail"]
    assert len(submitted) == 0


# ============================================================================
# Regression
# ============================================================================

def test_sprint1_2_3_4_regression():
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
