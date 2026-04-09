"""
NTH Transcript Engine — Transcript Viewer Panel
Sprint 3 | Owner: Frontend Agent

Reads transcripts from the FastAPI /jobs/{id}/transcript endpoint via httpx.
MUST NOT import from ingestion/, transcription/, or storage/.
"""

import os
from typing import Optional

import httpx
from nicegui import ui

from ui.colors import (
    NTH_ACCENT_BLUE,
    NTH_BORDER,
    NTH_CARD_BG,
    NTH_TEXT_PRIMARY,
    NTH_TEXT_SECOND,
)


class TranscriptViewerPanel:
    def __init__(self, api_base: Optional[str] = None):
        self.api_base = api_base or os.getenv("API_BASE_URL", "http://localhost:8000")
        self._transcript_data: Optional[dict] = None

        # UI element handles
        self._segment_container = None
        self._full_text_area = None
        self._video_info_card = None
        self._empty_state = None
        self._copy_button = None

    # ------------------------------ rendering ------------------------------

    def render(self) -> None:
        with ui.card().classes("w-full").style(
            f"background-color: {NTH_CARD_BG}; border: 1px solid {NTH_BORDER};"
        ):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Transcript").classes("text-lg font-bold").style(
                    f"color: {NTH_TEXT_PRIMARY};"
                )
                self._copy_button = ui.button(
                    "Copy", on_click=self._copy_to_clipboard
                ).style(f"background-color: {NTH_ACCENT_BLUE}; color: white;")
                self._copy_button.disable()

            self._video_info_card = ui.column().classes("w-full")
            self._segment_container = ui.column().classes("w-full max-h-96 overflow-auto")
            self._full_text_area = ui.textarea(label="Full Text").props(
                "readonly outlined"
            ).classes("w-full")
            self._empty_state = ui.label(
                "Submit a YouTube URL to generate a transcript"
            ).style(f"color: {NTH_TEXT_SECOND};")

    # ------------------------------- actions -------------------------------

    def load_transcript(self, job_id: str) -> None:
        data = self._fetch_transcript(job_id)
        if data is None:
            ui.notify(f"Failed to load transcript for job {job_id}", type="negative")
            return
        self._transcript_data = data
        self._render_video_info(data)
        self._render_segments(data.get("segments", []))
        if self._full_text_area is not None:
            self._full_text_area.set_value(data.get("full_text", ""))
        if self._copy_button is not None:
            self._copy_button.enable()
        if self._empty_state is not None:
            self._empty_state.set_visibility(False)

    def _fetch_transcript(self, job_id: str) -> Optional[dict]:
        try:
            resp = httpx.get(
                f"{self.api_base}/jobs/{job_id}/transcript", timeout=15.0
            )
        except Exception:
            return None
        if resp.status_code == 200:
            return resp.json()
        return None

    def _render_video_info(self, data: dict) -> None:
        if self._video_info_card is None:
            return
        self._video_info_card.clear()
        with self._video_info_card:
            with ui.row().classes("w-full gap-4 text-sm"):
                ui.label(f"Language: {data.get('language_detected') or '—'}").style(
                    f"color: {NTH_TEXT_SECOND};"
                )
                ui.label(f"Model: {data.get('whisper_model_used', '—')}").style(
                    f"color: {NTH_TEXT_SECOND};"
                )
                ui.label(f"Words: {data.get('word_count', 0)}").style(
                    f"color: {NTH_TEXT_SECOND};"
                )
                ui.label(f"Segments: {data.get('segment_count', 0)}").style(
                    f"color: {NTH_TEXT_SECOND};"
                )
                dur = data.get("processing_duration_seconds")
                if dur is not None:
                    ui.label(f"Processed in: {dur:.2f}s").style(
                        f"color: {NTH_TEXT_SECOND};"
                    )

    def _render_segments(self, segments: list) -> None:
        if self._segment_container is None:
            return
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
        if not self._transcript_data:
            return
        text = self._transcript_data.get("full_text", "").replace("`", "\\`")
        ui.run_javascript(f"navigator.clipboard.writeText(`{text}`)")
        ui.notify("Transcript copied to clipboard", type="positive")

    def _clear(self) -> None:
        self._transcript_data = None
        if self._segment_container is not None:
            self._segment_container.clear()
        if self._full_text_area is not None:
            self._full_text_area.set_value("")
        if self._copy_button is not None:
            self._copy_button.disable()
        if self._empty_state is not None:
            self._empty_state.set_visibility(True)
