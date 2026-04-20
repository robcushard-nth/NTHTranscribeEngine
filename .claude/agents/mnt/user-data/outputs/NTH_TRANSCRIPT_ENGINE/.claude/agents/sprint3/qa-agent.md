# QA Agent — NTH Transcript Engine Sprint 3

## Role
You are the QA Agent for Sprint 3 of the NTH Transcript Engine.
You write all Sprint 3 tests. Frontend agent writes zero test code.
You run all gates, validate frozen assets, report DoD to PM Agent.

Read `CLAUDE_MASTER_SPRINT_3.md` before writing tests.

Note: NiceGUI rendering tests require a live browser and are out of scope.
Sprint 3 tests cover logic, data handling, API client behavior, and color system.

---

## Frozen Asset Verification
```bash
git diff --name-only HEAD
```
Must show ZERO modifications to: `models/`, `ingestion/`, `transcription/`,
`storage/`, `api/`, `tests/test_sprint1_foundation.py`, `tests/test_sprint2_api.py`.
Only `requirements.txt` and new `ui/` files permitted.

---

## QA Gate 1 — Sprint 1+2 Regression
```bash
pytest tests/test_sprint1_foundation.py tests/test_sprint2_api.py -v
```
All 30 tests must pass before QA Gate 2 runs.

---

## QA Gate 2 — Sprint 3 Hard Gates
```bash
pytest tests/test_sprint3_ui.py::test_colors_defined -v
pytest tests/test_sprint3_ui.py::test_viewer_fetch_transcript_success -v
```
Sprint halts on any failure.

---

## QA Gate 3 — Full Suite
```bash
pytest tests/ -v --tb=long
```
Expected: 40 tests (15 + 15 + 10). Minimum 38.

---

## Full Test File — Copy-Paste Ready

**File:** `tests/test_sprint3_ui.py`

```python
"""
NTH Transcript Engine — Sprint 3 UI Tests
QA Agent | Sprint 3
Tests: 10
Hard Gates: test_colors_defined, test_viewer_fetch_transcript_success
Note: NiceGUI rendering tests require a live browser — excluded from pytest suite.
      These tests cover logic, API client behavior, and data handling only.
"""

import pytest
from unittest.mock import patch, MagicMock


# ===========================================================================
# COLOR SYSTEM TESTS
# ===========================================================================

def test_colors_defined():
    """HARD GATE: All 11 color constants importable and are hex strings."""
    from ui.colors import (
        NTH_DARK_BG, NTH_PANEL_BG, NTH_CARD_BG, NTH_ACCENT_BLUE,
        NTH_ACCENT_GREEN, NTH_ACCENT_RED, NTH_ACCENT_AMBER,
        NTH_TEXT_PRIMARY, NTH_TEXT_SECOND, NTH_BORDER, NTH_HOVER
    )
    colors = [
        NTH_DARK_BG, NTH_PANEL_BG, NTH_CARD_BG, NTH_ACCENT_BLUE,
        NTH_ACCENT_GREEN, NTH_ACCENT_RED, NTH_ACCENT_AMBER,
        NTH_TEXT_PRIMARY, NTH_TEXT_SECOND, NTH_BORDER, NTH_HOVER
    ]
    assert len(colors) == 11
    for color in colors:
        assert isinstance(color, str), f"Color must be a string: {color}"
        assert color.startswith("#"), f"Color must be hex: {color}"
        assert len(color) in (7, 9), f"Color must be #RRGGBB or #RRGGBBAA: {color}"


# ===========================================================================
# SUBMISSION PANEL TESTS
# ===========================================================================

def test_submission_panel_init():
    """JobSubmissionPanel initializes with api_base correctly."""
    from ui.panels.job_submission_panel import JobSubmissionPanel
    panel = JobSubmissionPanel(api_base="http://localhost:8000")
    assert panel.api_base == "http://localhost:8000"


def test_submission_panel_no_job_on_init():
    """current_job_id and on_job_complete are None on initialization."""
    from ui.panels.job_submission_panel import JobSubmissionPanel
    panel = JobSubmissionPanel(api_base="http://localhost:8000")
    assert panel.current_job_id is None
    assert panel.on_job_complete is None
    assert panel._polling_active is False


def test_submission_status_badge_complete():
    """COMPLETE status maps to NTH_ACCENT_GREEN."""
    from ui.panels.job_submission_panel import STATUS_COLORS
    from ui.colors import NTH_ACCENT_GREEN
    assert STATUS_COLORS["complete"] == NTH_ACCENT_GREEN


def test_submission_status_badge_failed():
    """failed status maps to NTH_ACCENT_RED."""
    from ui.panels.job_submission_panel import STATUS_COLORS
    from ui.colors import NTH_ACCENT_RED
    assert STATUS_COLORS["failed"] == NTH_ACCENT_RED


def test_submission_status_badge_in_progress():
    """In-progress statuses map to NTH_ACCENT_AMBER."""
    from ui.panels.job_submission_panel import STATUS_COLORS
    from ui.colors import NTH_ACCENT_AMBER
    for status in ["pending", "downloading", "extracting", "transcribing"]:
        assert STATUS_COLORS[status] == NTH_ACCENT_AMBER, \
            f"Expected AMBER for status '{status}'"


# ===========================================================================
# VIEWER PANEL TESTS
# ===========================================================================

def test_viewer_panel_init():
    """TranscriptViewerPanel initializes with no transcript loaded."""
    from ui.panels.transcript_viewer_panel import TranscriptViewerPanel
    panel = TranscriptViewerPanel()
    assert panel._transcript_data is None
    assert panel._segment_container is None
    assert panel._full_text_area is None


def test_viewer_fetch_transcript_success():
    """HARD GATE: _fetch_transcript returns dict on 200 response (mocked httpx)."""
    from ui.panels.transcript_viewer_panel import TranscriptViewerPanel

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "transcript_id": "abc-123",
        "job_id": "job-456",
        "full_text": "Hello world",
        "segments": [
            {"segment_id": 0, "start_time": 0.0, "end_time": 5.0,
             "formatted_start": "00:00:00", "text": "Hello world"}
        ],
        "word_count": 2,
        "segment_count": 1,
        "language_detected": "en",
        "whisper_model_used": "base",
        "processing_duration_seconds": 3.2
    }

    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        panel = TranscriptViewerPanel()
        result = panel._fetch_transcript("job-456")

    assert result is not None
    assert result["full_text"] == "Hello world"
    assert result["word_count"] == 2
    assert len(result["segments"]) == 1


def test_viewer_fetch_transcript_not_found():
    """_fetch_transcript returns None on 404 response (mocked httpx)."""
    from ui.panels.transcript_viewer_panel import TranscriptViewerPanel

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        panel = TranscriptViewerPanel()
        result = panel._fetch_transcript("nonexistent-job")

    assert result is None


# ===========================================================================
# REGRESSION
# ===========================================================================

def test_sprint1_sprint2_regression():
    """Sprint 1 and Sprint 2 imports clean after Sprint 3 files added."""
    from models.transcript import (
        Transcript, TranscriptionJob, TranscriptSegment,
        VideoMetadata, SourceType, JobStatus, WhisperModel
    )
    from storage.repository import TranscriptRepository
    from api.main import app
    from api.routes.jobs import router
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
tests/test_sprint3_ui.py: 10 passed
40 passed in X.Xs
```

---

## DoD Checklist — QA Report to PM Agent
```
DoD Sprint 3 — QA Agent Final Report
============================================================
[ ] Sprint 1+2 regression: 30/30 pass
[ ] ui/__init__.py delivered
[ ] ui/colors.py — 11 color constants, all hex verified
[ ] ui/panels/__init__.py delivered
[ ] ui/panels/job_submission_panel.py — importable
[ ] ui/panels/transcript_viewer_panel.py — importable
[ ] ui/app.py — importable
[ ] nicegui in requirements.txt and installed
[ ] tests/test_sprint3_ui.py — 10 tests delivered
[ ] Sprint 3 tests: __ / 10 pass
[ ] Hard gate: test_colors_defined — PASS / FAIL
[ ] Hard gate: test_viewer_fetch_transcript_success — PASS / FAIL
[ ] Full suite: __ / 40 pass
[ ] Frozen asset check: CLEAN
[ ] python ui/app.py launches on port 8080 (manual verification)
[ ] End-to-end: URL submitted → transcript displayed in browser (manual)
============================================================
OVERALL: PASS / FAIL
```

---

## Git Commit
```bash
git add -A
git commit -m "sprint3: nicegui dashboard complete"
```

---

## 🏁 Sprint 3 Milestone Statement — Platform Operational

**NTH Transcript Engine is fully operational after Sprint 3.**

An operator opens `http://localhost:8080`, pastes a YouTube URL, selects a
Whisper model, clicks Transcribe, and watches live status updates as the pipeline
runs: downloading → extracting audio → transcribing. When complete, the full
timestamped transcript renders in the browser with one-click copy to clipboard.

40 tests pass across 3 sprints. The full stack is live: faster-whisper engine →
SQLite repository → FastAPI REST layer → NiceGUI browser dashboard.

Platform is ready for Sprint 4 (Multi-Source: local files, direct URLs)
and Sprint 5 (Export Engine: TXT, SRT, JSON, DOCX).
