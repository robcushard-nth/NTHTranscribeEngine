"""
NTH Transcript Engine — NiceGUI Application Entry Point
Sprint 3 | Owner: Frontend Agent
Launch: python ui/app.py
Requires: API running on http://localhost:8000
"""

import os

from dotenv import load_dotenv
from nicegui import ui

from ui.colors import (
    NTH_ACCENT_BLUE,
    NTH_BORDER,
    NTH_DARK_BG,
    NTH_PANEL_BG,
    NTH_TEXT_PRIMARY,
)
from ui.panels.job_submission_panel import JobSubmissionPanel
from ui.panels.transcript_viewer_panel import TranscriptViewerPanel

load_dotenv()
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def build_dashboard() -> None:
    """Construct the single-page dashboard layout."""
    ui.query("body").style(
        f"background-color: {NTH_DARK_BG}; margin: 0; padding: 0;"
    )

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

    # Main two-column layout
    with ui.row().classes("w-full gap-4 p-6"):
        with ui.column().classes("w-1/3"):
            submission_panel = JobSubmissionPanel(api_base=API_BASE)
            submission_panel.render()

        with ui.column().classes("w-2/3"):
            viewer_panel = TranscriptViewerPanel(api_base=API_BASE)
            viewer_panel.render()

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
        reload=False,
    )
