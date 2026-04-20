# Frontend Agent — NTH Transcript Engine Sprint 3

## Role
You are the Frontend Agent for Sprint 3 of the NTH Transcript Engine.
You build all NiceGUI UI files. You do not write tests. You do not modify frozen files.
You report to PM Agent after each phase.

Read `CLAUDE_MASTER_SPRINT_3.md` before writing any code.

---

## Frozen Assets — Do Not Touch
- Everything in `models/`, `ingestion/`, `transcription/`, `storage/`, `api/`
- `tests/test_sprint1_foundation.py`, `tests/test_sprint2_api.py`

Permitted: append `nicegui>=1.4.0` to `requirements.txt` only.

---

## Hard Rules
1. UI panels import from `models.transcript` only — never from `ingestion/`, `transcription/`, `storage/`, or `api/` directly
2. All API calls use `httpx` — no `requests`, no `urllib`
3. All color values come from `ui.colors` — no hardcoded hex strings in panels
4. `asyncio` for polling loops — not `threading`
5. NiceGUI `ui.notify()` for user-facing errors — not print statements
6. No test code written by frontend agent

---

## Prerequisite Import Verification

Before writing any Sprint 3 UI code, run:
```bash
python -c "
from models.transcript import Transcript, TranscriptSegment
from storage.repository import TranscriptRepository
from api.main import app
from api.routes.jobs import router
print('Sprint 1+2 backend: OK — safe to build UI')
"
```
Report result to PM Agent. Do not write UI code if this fails.

---

## Phase 3a — Color System + Package Inits

### `ui/__init__.py`
```python
"""NTH Transcript Engine — UI Package"""
```

### `ui/panels/__init__.py`
```python
"""NTH Transcript Engine — UI Panels"""
```

### `ui/colors.py`
Implement exactly as specified in CLAUDE_MASTER_SPRINT_3.md.
All 11 constants must be present.

**Self-check:**
```bash
python -c "
from ui.colors import (
    NTH_DARK_BG, NTH_PANEL_BG, NTH_CARD_BG, NTH_ACCENT_BLUE,
    NTH_ACCENT_GREEN, NTH_ACCENT_RED, NTH_ACCENT_AMBER,
    NTH_TEXT_PRIMARY, NTH_TEXT_SECOND, NTH_BORDER, NTH_HOVER
)
assert all(c.startswith('#') for c in [
    NTH_DARK_BG, NTH_PANEL_BG, NTH_CARD_BG, NTH_ACCENT_BLUE,
    NTH_ACCENT_GREEN, NTH_ACCENT_RED, NTH_ACCENT_AMBER,
    NTH_TEXT_PRIMARY, NTH_TEXT_SECOND, NTH_BORDER, NTH_HOVER
])
print('Phase 3a: PASS — 11 color constants verified')
"
```

---

## Phase 3b — Job Submission Panel

### `ui/panels/job_submission_panel.py`

Full implementation:

```python
"""
NTH Transcript Engine — Job Submission Panel
Sprint 3 | Owner: Frontend Agent
Handles URL input, job submission, and live status polling.
"""

import asyncio
import httpx
from typing import Optional, Callable
from nicegui import ui
from ui.colors import (
    NTH_PANEL_BG, NTH_CARD_BG, NTH_ACCENT_BLUE, NTH_ACCENT_GREEN,
    NTH_ACCENT_RED, NTH_ACCENT_AMBER, NTH_TEXT_PRIMARY, NTH_TEXT_SECOND, NTH_BORDER
)

STATUS_COLORS = {
    "pending":      NTH_ACCENT_AMBER,
    "downloading":  NTH_ACCENT_AMBER,
    "extracting":   NTH_ACCENT_AMBER,
    "transcribing": NTH_ACCENT_AMBER,
    "complete":     NTH_ACCENT_GREEN,
    "failed":       NTH_ACCENT_RED,
}

STATUS_LABELS = {
    "pending":      "⏳ Pending",
    "downloading":  "⬇ Downloading",
    "extracting":   "🔊 Extracting Audio",
    "transcribing": "🧠 Transcribing",
    "complete":     "✅ Complete",
    "failed":       "❌ Failed",
}


class JobSubmissionPanel:
    def __init__(self, api_base: str):
        self.api_base = api_base
        self.current_job_id: Optional[str] = None
        self.on_job_complete: Optional[Callable] = None
        self._polling_active: bool = False

        # UI element references (set during render)
        self._url_input = None
        self._model_select = None
        self._submit_btn = None
        self._status_badge = None
        self._job_id_label = None
        self._error_label = None

    def render(self) -> None:
        """Build all UI elements."""
        with ui.card().classes("w-full").style(
            f"background-color: {NTH_PANEL_BG}; border: 1px solid {NTH_BORDER};"
            f" border-radius: 8px; padding: 20px;"
        ):
            ui.label("Submit Video").classes("text-lg font-bold mb-4").style(
                f"color: {NTH_TEXT_PRIMARY};"
            )

            # URL Input
            ui.label("YouTube URL").classes("text-sm mb-1").style(
                f"color: {NTH_TEXT_SECOND};"
            )
            self._url_input = ui.input(
                placeholder="https://www.youtube.com/watch?v=..."
            ).classes("w-full mb-4").style(
                f"color: {NTH_TEXT_PRIMARY};"
            )

            # Model Selector
            ui.label("Whisper Model").classes("text-sm mb-1").style(
                f"color: {NTH_TEXT_SECOND};"
            )
            self._model_select = ui.select(
                options=["tiny", "base", "small", "medium", "large-v3"],
                value="base"
            ).classes("w-full mb-4")

            # Model guidance
            with ui.row().classes("w-full mb-4 gap-2"):
                for model, desc in [
                    ("tiny", "Fastest"), ("base", "Balanced"),
                    ("small", "Better"), ("large-v3", "Best")
                ]:
                    ui.label(f"{model}: {desc}").classes("text-xs").style(
                        f"color: {NTH_TEXT_SECOND};"
                    )

            # Submit Button
            self._submit_btn = ui.button(
                "Transcribe",
                on_click=self._submit
            ).classes("w-full").style(
                f"background-color: {NTH_ACCENT_BLUE}; color: white;"
                f" font-weight: bold; padding: 10px;"
            )

            # Status Section
            ui.separator().classes("my-4")

            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Status").classes("text-sm").style(
                    f"color: {NTH_TEXT_SECOND};"
                )
                self._status_badge = ui.label("—").classes("text-sm font-mono").style(
                    f"color: {NTH_TEXT_SECOND};"
                )

            self._job_id_label = ui.label("").classes("text-xs font-mono mt-2").style(
                f"color: {NTH_TEXT_SECOND};"
            )

            self._error_label = ui.label("").classes("text-sm mt-2").style(
                f"color: {NTH_ACCENT_RED};"
            )
            self._error_label.set_visibility(False)

    def _submit(self) -> None:
        """POST to /jobs API endpoint."""
        url = self._url_input.value.strip()
        if not url:
            ui.notify("Please enter a YouTube URL", type="warning")
            return

        self._submit_btn.disable()
        self._error_label.set_visibility(False)
        self._status_badge.set_text("⏳ Submitting...")
        self._status_badge.style(f"color: {NTH_ACCENT_AMBER};")

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.api_base}/jobs/",
                    json={"url": url, "whisper_model": self._model_select.value}
                )
            if resp.status_code == 202:
                data = resp.json()
                self.current_job_id = data["job_id"]
                self._job_id_label.set_text(f"Job: {self.current_job_id[:8]}...")
                ui.timer(3.0, self._poll_status, once=False)
            elif resp.status_code == 400:
                self._show_error("Invalid URL. Must be a YouTube link.")
                self._reset()
            else:
                self._show_error(f"API error: {resp.status_code}")
                self._reset()
        except httpx.ConnectError:
            self._show_error("Cannot connect to API. Is the server running on port 8000?")
            self._reset()
        except Exception as e:
            self._show_error(f"Error: {str(e)}")
            self._reset()

    def _poll_status(self) -> None:
        """Poll job status. Called by ui.timer every 3 seconds."""
        if not self.current_job_id or not self._polling_active:
            return
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.api_base}/jobs/{self.current_job_id}")
            if resp.status_code == 200:
                data = resp.json()
                status = data["status"]
                self._update_status_badge(status)
                if status == "complete":
                    self._polling_active = False
                    if self.on_job_complete:
                        self.on_job_complete(self.current_job_id)
                    ui.notify("Transcription complete!", type="positive")
                    self._reset()
                elif status == "failed":
                    self._polling_active = False
                    self._show_error(data.get("error_message", "Job failed."))
                    self._reset()
        except Exception as e:
            self._show_error(f"Polling error: {str(e)}")

    def _update_status_badge(self, status: str) -> None:
        color = STATUS_COLORS.get(status, NTH_TEXT_SECOND)
        label = STATUS_LABELS.get(status, status)
        self._status_badge.set_text(label)
        self._status_badge.style(f"color: {color};")

    def _show_error(self, message: str) -> None:
        self._error_label.set_text(message)
        self._error_label.set_visibility(True)

    def _reset(self) -> None:
        self._submit_btn.enable()

    def start_polling(self) -> None:
        self._polling_active = True

    def stop_polling(self) -> None:
        self._polling_active = False
```

**Self-check:**
```bash
python -c "
from ui.panels.job_submission_panel import JobSubmissionPanel, STATUS_COLORS, STATUS_LABELS
panel = JobSubmissionPanel(api_base='http://localhost:8000')
assert panel.current_job_id is None
assert panel.on_job_complete is None
assert 'complete' in STATUS_COLORS
assert STATUS_COLORS['complete'] is not None
print('Phase 3b: PASS')
"
```

---

## Phase 3c — Transcript Viewer Panel

### `ui/panels/transcript_viewer_panel.py`

```python
"""
NTH Transcript Engine — Transcript Viewer Panel
Sprint 3 | Owner: Frontend Agent
Displays timestamped transcript segments and full text.
"""

import httpx
from typing import Optional
from nicegui import ui
from ui.colors import (
    NTH_PANEL_BG, NTH_CARD_BG, NTH_ACCENT_BLUE, NTH_ACCENT_GREEN,
    NTH_TEXT_PRIMARY, NTH_TEXT_SECOND, NTH_BORDER
)


class TranscriptViewerPanel:
    def __init__(self):
        self._transcript_data: Optional[dict] = None
        self._api_base: str = "http://localhost:8000"
        self._segment_container = None
        self._full_text_area = None
        self._video_info_card = None
        self._empty_state = None
        self._content_area = None

    def render(self) -> None:
        """Build all UI elements. Empty state shown initially."""
        with ui.card().classes("w-full").style(
            f"background-color: {NTH_PANEL_BG}; border: 1px solid {NTH_BORDER};"
            f" border-radius: 8px; padding: 20px; min-height: 600px;"
        ):
            # Header
            with ui.row().classes("w-full items-center justify-between mb-4"):
                ui.label("Transcript").classes("text-lg font-bold").style(
                    f"color: {NTH_TEXT_PRIMARY};"
                )
                ui.button(
                    "Copy Text",
                    on_click=self._copy_to_clipboard
                ).classes("text-sm").style(
                    f"background-color: transparent; color: {NTH_ACCENT_BLUE};"
                    f" border: 1px solid {NTH_ACCENT_BLUE};"
                )

            ui.separator().classes("mb-4")

            # Empty state
            with ui.column().classes("w-full items-center justify-center py-16") as self._empty_state:
                ui.icon("video_library", size="48px").style(
                    f"color: {NTH_TEXT_SECOND};"
                )
                ui.label("Submit a YouTube URL to generate a transcript").classes(
                    "text-center mt-4"
                ).style(f"color: {NTH_TEXT_SECOND};")

            # Content area (hidden until transcript loads)
            with ui.column().classes("w-full") as self._content_area:
                # Video info card
                self._video_info_card = ui.card().classes("w-full mb-4").style(
                    f"background-color: {NTH_CARD_BG}; border: 1px solid {NTH_BORDER};"
                )

                # Tabs: Segments | Full Text
                with ui.tabs().classes("w-full") as tabs:
                    seg_tab = ui.tab("Segments")
                    text_tab = ui.tab("Full Text")

                with ui.tab_panels(tabs, value=seg_tab).classes("w-full"):
                    with ui.tab_panel(seg_tab):
                        with ui.scroll_area().classes("w-full").style("height: 400px;"):
                            self._segment_container = ui.column().classes("w-full")

                    with ui.tab_panel(text_tab):
                        self._full_text_area = ui.textarea().classes("w-full").style(
                            "height: 400px; font-size: 14px;"
                        ).props("readonly outlined")

            self._content_area.set_visibility(False)

    def load_transcript(self, job_id: str) -> None:
        """Called by submission panel on COMPLETE. Fetches and renders transcript."""
        data = self._fetch_transcript(job_id)
        if not data:
            ui.notify("Could not load transcript.", type="negative")
            return
        self._transcript_data = data
        self._render_video_info(data)
        self._render_segments(data.get("segments", []))
        if self._full_text_area:
            self._full_text_area.set_value(data.get("full_text", ""))
        self._empty_state.set_visibility(False)
        self._content_area.set_visibility(True)

    def _fetch_transcript(self, job_id: str) -> Optional[dict]:
        """GET /jobs/{id}/transcript. Returns parsed JSON or None."""
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{self._api_base}/jobs/{job_id}/transcript")
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None

    def _render_video_info(self, data: dict) -> None:
        self._video_info_card.clear()
        with self._video_info_card:
            with ui.grid(columns=3).classes("w-full gap-2 p-3"):
                for label, value in [
                    ("Words", str(data.get("word_count", "—"))),
                    ("Segments", str(data.get("segment_count", "—"))),
                    ("Language", data.get("language_detected", "—").upper()),
                    ("Model", data.get("whisper_model_used", "—")),
                    ("Duration", f"{data.get('processing_duration_seconds', 0):.1f}s"),
                ]:
                    with ui.column().classes("items-center"):
                        ui.label(value).classes("text-lg font-bold").style(
                            f"color: {NTH_ACCENT_GREEN};"
                        )
                        ui.label(label).classes("text-xs").style(
                            f"color: {NTH_TEXT_SECOND};"
                        )

    def _render_segments(self, segments: list[dict]) -> None:
        self._segment_container.clear()
        with self._segment_container:
            for seg in segments:
                with ui.row().classes("w-full items-start gap-3 py-2").style(
                    f"border-bottom: 1px solid {NTH_BORDER};"
                ):
                    ui.label(seg.get("formatted_start", "00:00:00")).classes(
                        "font-mono text-sm w-20 shrink-0"
                    ).style(f"color: {NTH_ACCENT_BLUE};")
                    ui.label(seg.get("text", "")).classes("text-sm").style(
                        f"color: {NTH_TEXT_PRIMARY};"
                    )

    def _copy_to_clipboard(self) -> None:
        if self._transcript_data:
            text = self._transcript_data.get("full_text", "")
            ui.run_javascript(f"""
                navigator.clipboard.writeText({repr(text)}).then(() => {{
                    console.log('Transcript copied to clipboard');
                }});
            """)
            ui.notify("Transcript copied to clipboard!", type="positive")
        else:
            ui.notify("No transcript to copy.", type="warning")

    def _clear(self) -> None:
        self._transcript_data = None
        if self._segment_container:
            self._segment_container.clear()
        if self._full_text_area:
            self._full_text_area.set_value("")
        self._empty_state.set_visibility(True)
        self._content_area.set_visibility(False)
```

**Self-check:**
```bash
python -c "
from ui.panels.transcript_viewer_panel import TranscriptViewerPanel
panel = TranscriptViewerPanel()
assert panel._transcript_data is None
print('Phase 3c: PASS')
"
```

---

## Phase 3d — App Entry Point

### `ui/app.py`
Implement exactly as specified in CLAUDE_MASTER_SPRINT_3.md.

**Self-check (import only — do not launch server in check):**
```bash
python -c "
from ui.app import build_dashboard
from ui.panels.job_submission_panel import JobSubmissionPanel
from ui.panels.transcript_viewer_panel import TranscriptViewerPanel
from ui.colors import NTH_DARK_BG
print('Phase 3d: PASS — all imports clean')
"
```

---

## Quality Gates Self-Checklist

```
[ ] ui/__init__.py — exists
[ ] ui/colors.py — 11 color constants, all hex strings
[ ] ui/panels/__init__.py — exists
[ ] ui/panels/job_submission_panel.py — JobSubmissionPanel, STATUS_COLORS, STATUS_LABELS importable
[ ] ui/panels/transcript_viewer_panel.py — TranscriptViewerPanel importable
[ ] ui/app.py — build_dashboard, index importable
[ ] nicegui appended to requirements.txt and installed
[ ] All self-checks returned PASS
[ ] No hardcoded hex strings in panels — all from ui.colors
[ ] No direct imports from ingestion/, transcription/, storage/ in any UI file
[ ] All API calls use httpx
[ ] No test code written by frontend agent
[ ] models/transcript.py not modified
```
