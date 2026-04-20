# CLAUDE_MASTER_SPRINT_3.md
**Project:** NTH Transcript Engine
**Sprint:** 3 — NiceGUI Dashboard
**Module:** Job Submission Panel · Live Status Polling · Transcript Viewer · UI Entry Point
**Author:** William "Rob" Cushard — NTH AI Dynamics
**Git Author:** `robcushard-nth <rob.cushard@nthsimplesolution.com>`
**Repo:** `C:\Users\RobCushard\NTH_TRANSCRIPT_ENGINE\`
**Agent Path:** `.claude\agents\`
**Date:** 2026-04-09
**Status:** 🔴 NOT STARTED — Requires Sprint 2 COMPLETE

---

## Sprint Mission

Sprint 3 delivers the operator-facing interface. After this sprint, an operator
opens a browser, pastes a YouTube URL, selects a Whisper model, clicks Transcribe,
watches the job status update live, and reads the full timestamped transcript in
the browser — all without touching a terminal or a curl command.

The UI is built with NiceGUI: a Python-native UI framework that runs a local web
server and renders a reactive browser interface. The frontend talks exclusively to
the Sprint 2 FastAPI endpoints via httpx — it never calls ingestion or transcription
code directly. The API must be running on localhost:8000 before the UI is launched.

All Sprint 1 and Sprint 2 files are frozen. Sprint 3 adds new files only.

---

## Scope Boundary

### IN SCOPE — Sprint 3
- `ui/__init__.py`
- `ui/app.py` — NiceGUI entry point, dashboard layout, panel registration
- `ui/panels/__init__.py`
- `ui/panels/job_submission_panel.py` — URL input, model selector, submit, live status
- `ui/panels/transcript_viewer_panel.py` — segment list, full text view, copy button
- `ui/colors.py` — NTH color system constants
- `tests/test_sprint3_ui.py` — QA agent writes this (logic tests, not rendering tests)
- Minimum 10 pytest tests
- `requirements.txt` updated (append nicegui)

### OUT OF SCOPE — Sprint 3
- Export file downloads: TXT, SRT, DOCX (Sprint 5)
- Local file upload drag-and-drop (Sprint 4)
- Multi-job queue management (post-roadmap)
- User authentication (post-roadmap)
- Dark/light mode toggle (post-roadmap)
- Any modification to FastAPI routes (Sprint 2 frozen)

---

## Frozen Assets — Sprint 3 Must Not Modify

| File | Frozen Since |
|---|---|
| `models/transcript.py` | Sprint 1 |
| `ingestion/youtube_handler.py` | Sprint 1 |
| `transcription/audio_extractor.py` | Sprint 1 |
| `transcription/engine.py` | Sprint 1 |
| `storage/repository.py` | Sprint 2 |
| `api/main.py` | Sprint 2 |
| `api/job_processor.py` | Sprint 2 |
| `api/routes/jobs.py` | Sprint 2 |
| `tests/test_sprint1_foundation.py` | Sprint 1 |
| `tests/test_sprint2_api.py` | Sprint 2 |

Permitted modification: `requirements.txt` (append `nicegui` only)

---

## Color System — `ui/colors.py`

```python
# ui/colors.py
"""NTH Transcript Engine — UI Color System"""

NTH_DARK_BG     = "#0D1117"
NTH_PANEL_BG    = "#161B22"
NTH_CARD_BG     = "#1C2128"
NTH_ACCENT_BLUE = "#2563EB"
NTH_ACCENT_GREEN= "#10B981"
NTH_ACCENT_RED  = "#EF4444"
NTH_ACCENT_AMBER= "#F59E0B"
NTH_TEXT_PRIMARY= "#F0F6FC"
NTH_TEXT_SECOND = "#8B949E"
NTH_BORDER      = "#30363D"
NTH_HOVER       = "#21262D"
```

All panels import from `ui.colors`. No panel defines its own color constants.

---

## Module Specifications

### Module 1: `ui/app.py`

**Responsibility:** Initialize the NiceGUI application, set global styles,
register both panels, and launch the local web server.

```python
"""
NTH Transcript Engine — NiceGUI Application Entry Point
Sprint 3 | Owner: Frontend Agent
Launch: python ui/app.py
Requires: API running on http://localhost:8000
"""

import os
from dotenv import load_dotenv
import nicegui.globals
from nicegui import ui, app as nicegui_app
from ui.panels.job_submission_panel import JobSubmissionPanel
from ui.panels.transcript_viewer_panel import TranscriptViewerPanel
from ui.colors import (
    NTH_DARK_BG, NTH_PANEL_BG, NTH_TEXT_PRIMARY, NTH_ACCENT_BLUE, NTH_BORDER
)

load_dotenv()
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def build_dashboard() -> None:
    """Construct the single-page dashboard layout."""
    ui.query("body").style(f"background-color: {NTH_DARK_BG}; margin: 0; padding: 0;")

    # Header
    with ui.row().classes("w-full items-center justify-between px-6 py-3").style(
        f"background-color: {NTH_PANEL_BG}; border-bottom: 1px solid {NTH_BORDER};"
    ):
        ui.label("NTH Transcript Engine").classes("text-xl font-bold").style(
            f"color: {NTH_TEXT_PRIMARY};"
        )
        ui.label("NTH AI Dynamics").classes("text-sm").style(
            f"color: {NTH_ACCENT_BLUE};"
        )

    # Main layout — two-column
    with ui.row().classes("w-full gap-4 p-6"):
        # Left column — submission panel
        with ui.column().classes("w-1/3"):
            submission_panel = JobSubmissionPanel(api_base=API_BASE)
            submission_panel.render()

        # Right column — transcript viewer
        with ui.column().classes("w-2/3"):
            viewer_panel = TranscriptViewerPanel()
            viewer_panel.render()

        # Wire panels: submission triggers viewer refresh
        submission_panel.on_job_complete = viewer_panel.load_transcript


@ui.page("/")
def index():
    build_dashboard()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("UI_PORT", "8080")),
        title="NTH Transcript Engine",
        dark=True,
        reload=False
    )
```

---

### Module 2: `ui/panels/job_submission_panel.py`

**Responsibility:** Accept a YouTube URL, submit to the API, poll status every
3 seconds, display live status badge, and notify the viewer panel on completion.

**Required UI sections:**
1. **Source Input** — text input labeled "YouTube URL", placeholder text, full width
2. **Model Selector** — dropdown: tiny / base / small / medium / large-v3 (default: base)
3. **Submit Button** — "Transcribe" button, NTH_ACCENT_BLUE, disabled during processing
4. **Status Badge** — colored label showing current job status (updates every 3 seconds)
5. **Job Info** — job_id display (truncated to 8 chars) and created_at timestamp

**Status badge colors:**
- `pending` / `downloading` / `extracting` / `transcribing` → NTH_ACCENT_AMBER
- `complete` → NTH_ACCENT_GREEN
- `failed` → NTH_ACCENT_RED

**Class interface:**
```python
class JobSubmissionPanel:
    def __init__(self, api_base: str):
        self.api_base = api_base
        self.current_job_id: Optional[str] = None
        self.on_job_complete: Optional[callable] = None  # callback to viewer panel
        self._polling_active: bool = False

    def render(self) -> None:
        """Build all UI elements. Called once during dashboard construction."""

    def _submit(self) -> None:
        """POST to /jobs. Start polling on success. Disable submit button."""

    async def _poll_status(self) -> None:
        """GET /jobs/{id} every 3 seconds. Update badge. Call on_job_complete when COMPLETE."""

    def _update_status_badge(self, status: str) -> None:
        """Set badge label text and color based on status string."""

    def _reset(self) -> None:
        """Re-enable submit button. Clear current job context."""
```

**Polling logic:**
```python
async def _poll_status(self) -> None:
    self._polling_active = True
    while self._polling_active:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.api_base}/jobs/{self.current_job_id}")
            if resp.status_code == 200:
                data = resp.json()
                status = data["status"]
                self._update_status_badge(status)
                if status == "complete":
                    self._polling_active = False
                    if self.on_job_complete:
                        self.on_job_complete(self.current_job_id)
                    self._reset()
                    return
                elif status == "failed":
                    self._polling_active = False
                    self._reset()
                    return
        await asyncio.sleep(3)
```

---

### Module 3: `ui/panels/transcript_viewer_panel.py`

**Responsibility:** Accept a job_id from the submission panel, fetch the full
transcript from the API, render the timestamped segment list and full text view.

**Required UI sections:**
1. **Header row** — "Transcript" label + copy-to-clipboard button (right-aligned)
2. **Video info card** — title, uploader, duration, language detected, word count, segment count
3. **Segment list** — scrollable, each segment shows `[HH:MM:SS]` timestamp + text
4. **Full text area** — read-only textarea with the complete transcript text
5. **Empty state** — "Submit a YouTube URL to generate a transcript" message when no transcript loaded

**Class interface:**
```python
class TranscriptViewerPanel:
    def __init__(self):
        self._transcript_data: Optional[dict] = None
        self._segment_container = None
        self._full_text_area = None
        self._video_info_card = None

    def render(self) -> None:
        """Build all UI elements. Empty state shown initially."""

    def load_transcript(self, job_id: str) -> None:
        """Called by submission panel on COMPLETE. Fetches and renders transcript."""

    def _fetch_transcript(self, job_id: str) -> Optional[dict]:
        """GET /jobs/{id}/transcript via httpx (sync). Returns parsed JSON or None."""

    def _render_segments(self, segments: list[dict]) -> None:
        """Clear segment container and rebuild with new segments."""

    def _copy_to_clipboard(self) -> None:
        """Copy full_text to clipboard via ui.run_javascript."""

    def _clear(self) -> None:
        """Reset to empty state."""
```

**Segment rendering pattern:**
```python
def _render_segments(self, segments: list[dict]) -> None:
    self._segment_container.clear()
    with self._segment_container:
        for seg in segments:
            with ui.row().classes("w-full items-start gap-3 py-2").style(
                f"border-bottom: 1px solid {NTH_BORDER};"
            ):
                ui.label(seg["formatted_start"]).classes("font-mono text-sm w-20 shrink-0").style(
                    f"color: {NTH_ACCENT_BLUE};"
                )
                ui.label(seg["text"]).classes("text-sm").style(
                    f"color: {NTH_TEXT_PRIMARY};"
                )
```

---

## Updated requirements.txt (Full — Sprint 1 + 2 + 3)

```
# NTH Transcript Engine — All Sprint Dependencies
yt-dlp>=2024.1.0
faster-whisper>=1.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
pytest-asyncio>=0.23.0
nicegui>=1.4.0
```

---

## .env.example Additions

Add these two lines to `.env` (not .env.example modification — just document here):
```
API_BASE_URL=http://localhost:8000
UI_PORT=8080
```

---

## Directory Structure After Sprint 3

```
NTH_TRANSCRIPT_ENGINE/
├── CLAUDE_MASTER_SPRINT_3.md          ← This file
├── models/                            ← FROZEN (Sprint 1)
├── ingestion/                         ← FROZEN (Sprint 1)
├── transcription/                     ← FROZEN (Sprint 1)
├── storage/                           ← FROZEN (Sprint 2)
├── api/                               ← FROZEN (Sprint 2)
├── ui/
│   ├── __init__.py                    ← NEW (Sprint 3)
│   ├── app.py                         ← NEW (Sprint 3)
│   ├── colors.py                      ← NEW (Sprint 3)
│   └── panels/
│       ├── __init__.py                ← NEW (Sprint 3)
│       ├── job_submission_panel.py    ← NEW (Sprint 3)
│       └── transcript_viewer_panel.py ← NEW (Sprint 3)
├── tests/
│   ├── test_sprint1_foundation.py     ← FROZEN
│   ├── test_sprint2_api.py            ← FROZEN
│   └── test_sprint3_ui.py             ← NEW (Sprint 3) — QA agent writes
└── requirements.txt                   ← MODIFIED (append nicegui)
```

---

## Test Requirements — Sprint 3

**Minimum tests:** 10
**Test file:** `tests/test_sprint3_ui.py`
**Note:** UI rendering tests are not included (NiceGUI rendering requires a live browser).
Tests cover panel logic, API client calls (mocked), and data transformation.

| # | Test Name | What It Validates |
|---|---|---|
| 1 | `test_colors_defined` | All 11 color constants importable from ui.colors |
| 2 | `test_submission_panel_init` | JobSubmissionPanel initializes with api_base |
| 3 | `test_submission_panel_no_job_on_init` | current_job_id is None on init |
| 4 | `test_viewer_panel_init` | TranscriptViewerPanel initializes with no transcript |
| 5 | `test_viewer_fetch_transcript_success` | _fetch_transcript returns dict on 200 (mocked) |
| 6 | `test_viewer_fetch_transcript_not_found` | _fetch_transcript returns None on 404 (mocked) |
| 7 | `test_submission_status_badge_complete` | COMPLETE status maps to NTH_ACCENT_GREEN |
| 8 | `test_submission_status_badge_failed` | failed status maps to NTH_ACCENT_RED |
| 9 | `test_submission_status_badge_in_progress` | downloading/transcribing maps to AMBER |
| 10 | `test_sprint1_sprint2_regression` | All Sprint 1+2 imports clean after Sprint 3 files added |

**Hard Gate Tests:**
- `test_colors_defined` — color system integrity
- `test_viewer_fetch_transcript_success` — API integration logic

---

## Definition of Done — Sprint 3

- [ ] Sprint 1+2 regression: `pytest tests/test_sprint1_foundation.py tests/test_sprint2_api.py -v` — all 30 pass
- [ ] `ui/__init__.py` delivered
- [ ] `ui/colors.py` — all 11 color constants present
- [ ] `ui/app.py` — importable, `build_dashboard` and `index` defined
- [ ] `ui/panels/__init__.py` delivered
- [ ] `ui/panels/job_submission_panel.py` — JobSubmissionPanel importable
- [ ] `ui/panels/transcript_viewer_panel.py` — TranscriptViewerPanel importable
- [ ] `requirements.txt` updated with nicegui
- [ ] `tests/test_sprint3_ui.py` — minimum 10 tests
- [ ] Sprint 3 tests pass: `pytest tests/test_sprint3_ui.py -v`
- [ ] Full suite passes: `pytest tests/ -v` (40 total)
- [ ] Hard gate tests PASS
- [ ] `git diff --name-only` shows zero frozen file modifications
- [ ] `python ui/app.py` starts NiceGUI on port 8080 (with API running)
- [ ] Browser opens to `http://localhost:8080` and dashboard renders
- [ ] End-to-end manual: paste YouTube URL → click Transcribe → status updates → transcript appears
- [ ] git commit: `sprint3: nicegui dashboard complete`

---

## Launch Sequence (Full Stack)

Open two terminals:

**Terminal 1 — API:**
```bash
cd C:\Users\RobCushard\NTH_TRANSCRIPT_ENGINE
venv\Scripts\activate
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — UI:**
```bash
cd C:\Users\RobCushard\NTH_TRANSCRIPT_ENGINE
venv\Scripts\activate
python ui/app.py
```

Open browser: `http://localhost:8080`

---

## PM Agent Launch Prompt

```
You are the PM Agent for Sprint 3 of the NTH Transcript Engine.

Read CLAUDE_MASTER_SPRINT_3.md completely before taking any action.

Sprints 1 and 2 are complete and frozen. Your FIRST action is to run the
full Sprint 1+2 regression before any Sprint 3 code is written:

  pytest tests/test_sprint1_foundation.py tests/test_sprint2_api.py -v

All 30 tests must pass. Any failure — halt and report to user.

Execute in this sequence:
1. Sprint 1+2 regression (gate — must pass before proceeding)
2. Direct Frontend Agent Phase 3a: ui/colors.py + ui/__init__.py + ui/panels/__init__.py
3. Direct Frontend Agent Phase 3b: ui/panels/job_submission_panel.py
4. Direct Frontend Agent Phase 3c: ui/panels/transcript_viewer_panel.py
5. Direct Frontend Agent Phase 3d: ui/app.py
6. Direct Backend Agent to append nicegui to requirements.txt and pip install
7. Import verification for all new UI modules
8. QA Gate 1: Hard gate tests (colors + API fetch logic)
9. QA Gate 2: Full suite — pytest tests/ -v (40 total expected)
10. Verify frozen assets untouched: git diff --name-only HEAD
11. DoD report — explicit PASS/FAIL every item
12. git commit: sprint3: nicegui dashboard complete

Critical constraint: UI panels call FastAPI endpoints via httpx only.
They never import from ingestion/, transcription/, or storage/ directly.
The API must be running on localhost:8000 for manual end-to-end verification.
```
