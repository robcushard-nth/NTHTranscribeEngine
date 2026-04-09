"""
NTH Transcript Engine — Sprint 3 UI Tests
Owner: QA Agent

Logic-only tests. NiceGUI rendering is not tested (requires live browser).
"""

from unittest.mock import MagicMock, patch

import pytest

from ui import colors
from ui.colors import (
    NTH_ACCENT_AMBER,
    NTH_ACCENT_BLUE,
    NTH_ACCENT_GREEN,
    NTH_ACCENT_RED,
    NTH_BORDER,
    NTH_CARD_BG,
    NTH_DARK_BG,
    NTH_HOVER,
    NTH_PANEL_BG,
    NTH_TEXT_PRIMARY,
    NTH_TEXT_SECOND,
)
from ui.panels.job_submission_panel import JobSubmissionPanel, status_color
from ui.panels.transcript_viewer_panel import TranscriptViewerPanel


# --------------------------------- colors ------------------------------------

def test_colors_defined():
    expected = [
        "NTH_DARK_BG",
        "NTH_PANEL_BG",
        "NTH_CARD_BG",
        "NTH_ACCENT_BLUE",
        "NTH_ACCENT_GREEN",
        "NTH_ACCENT_RED",
        "NTH_ACCENT_AMBER",
        "NTH_TEXT_PRIMARY",
        "NTH_TEXT_SECOND",
        "NTH_BORDER",
        "NTH_HOVER",
    ]
    for name in expected:
        assert hasattr(colors, name), f"Missing color constant: {name}"
        value = getattr(colors, name)
        assert isinstance(value, str)
        assert value.startswith("#")
        assert len(value) == 7


# --------------------------- JobSubmissionPanel ------------------------------

def test_submission_panel_init():
    panel = JobSubmissionPanel(api_base="http://localhost:8000")
    assert panel.api_base == "http://localhost:8000"
    assert panel.on_job_complete is None
    assert panel._polling_active is False


def test_submission_panel_no_job_on_init():
    panel = JobSubmissionPanel(api_base="http://localhost:8000")
    assert panel.current_job_id is None


def test_submission_status_badge_complete():
    assert status_color("complete") == NTH_ACCENT_GREEN


def test_submission_status_badge_failed():
    assert status_color("failed") == NTH_ACCENT_RED


def test_submission_status_badge_in_progress():
    for s in ("pending", "downloading", "extracting", "transcribing"):
        assert status_color(s) == NTH_ACCENT_AMBER, f"{s} should be AMBER"


# -------------------------- TranscriptViewerPanel ----------------------------

def test_viewer_panel_init():
    panel = TranscriptViewerPanel(api_base="http://localhost:8000")
    assert panel._transcript_data is None
    assert panel._segment_container is None
    assert panel._full_text_area is None


def test_viewer_fetch_transcript_success():
    panel = TranscriptViewerPanel(api_base="http://localhost:8000")
    fake_payload = {
        "transcript_id": "abc",
        "job_id": "job-1",
        "full_text": "hello world",
        "language_detected": "en",
        "whisper_model_used": "base",
        "segment_count": 1,
        "word_count": 2,
        "processing_duration_seconds": 0.5,
        "segments": [
            {
                "segment_id": 0,
                "start_time": 0.0,
                "end_time": 1.0,
                "formatted_start": "00:00:00",
                "formatted_end": "00:00:01",
                "text": "hello world",
            }
        ],
        "created_at": "2026-04-09T00:00:00",
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_payload
    with patch(
        "ui.panels.transcript_viewer_panel.httpx.get", return_value=mock_resp
    ) as mock_get:
        result = panel._fetch_transcript("job-1")
    assert result == fake_payload
    mock_get.assert_called_once()
    assert "/jobs/job-1/transcript" in mock_get.call_args[0][0]


def test_viewer_fetch_transcript_not_found():
    panel = TranscriptViewerPanel(api_base="http://localhost:8000")
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch(
        "ui.panels.transcript_viewer_panel.httpx.get", return_value=mock_resp
    ):
        result = panel._fetch_transcript("missing-job")
    assert result is None


# --------------------------- Sprint 1+2 regression ---------------------------

def test_sprint1_sprint2_regression():
    """Sprint 1 + Sprint 2 imports must remain clean after Sprint 3."""
    from models.transcript import (  # noqa: F401
        JobStatus,
        SourceType,
        Transcript,
        TranscriptionJob,
        TranscriptSegment,
        VideoMetadata,
        WhisperModel,
    )
    from ingestion.youtube_handler import YouTubeHandler  # noqa: F401
    from transcription.audio_extractor import AudioExtractor  # noqa: F401
    from transcription.engine import TranscriptionEngine  # noqa: F401
    from storage.repository import TranscriptRepository  # noqa: F401
    from api.main import app  # noqa: F401
    from api.job_processor import JobProcessor  # noqa: F401
    from api.routes.jobs import (  # noqa: F401
        SubmitJobRequest,
        JobStatusResponse,
        TranscriptResponse,
        SegmentResponse,
        router,
    )
    assert TranscriptionJob().status is JobStatus.PENDING
