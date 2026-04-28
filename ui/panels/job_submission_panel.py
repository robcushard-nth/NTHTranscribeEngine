"""
NTH Transcript Engine — Job Submission Panel
Sprint 3 | Owner: Frontend Agent

The submission panel POSTs YouTube URLs to the FastAPI /jobs endpoint and polls
status. It MUST NOT import from ingestion/, transcription/, or storage/.
"""

from typing import Callable, Optional

import httpx
from nicegui import ui

from ui.colors import (
    NTH_ACCENT_AMBER,
    NTH_ACCENT_BLUE,
    NTH_ACCENT_GREEN,
    NTH_ACCENT_RED,
    NTH_BORDER,
    NTH_CARD_BG,
    NTH_TEXT_PRIMARY,
    NTH_TEXT_SECOND,
)


_IN_PROGRESS_STATUSES = {"pending", "downloading", "extracting", "transcribing"}


def status_color(status: str) -> str:
    """Pure mapping function — testable without rendering NiceGUI."""
    if status == "complete":
        return NTH_ACCENT_GREEN
    if status == "failed":
        return NTH_ACCENT_RED
    if status in _IN_PROGRESS_STATUSES:
        return NTH_ACCENT_AMBER
    return NTH_TEXT_SECOND


class JobSubmissionPanel:
    def __init__(self, api_base: str):
        self.api_base = api_base
        self.current_job_id: Optional[str] = None
        self.on_job_complete: Optional[Callable[[str], None]] = None
        self._polling_active: bool = False
        self._poll_timer = None

        # UI element handles (populated in render())
        self._url_input = None
        self._model_select = None
        self._submit_button = None
        self._status_badge = None
        self._job_id_label = None
        self._created_label = None

    # ------------------------------ rendering ------------------------------

    def render(self) -> None:
        with ui.card().classes("w-full").style(
            f"background-color: {NTH_CARD_BG}; border: 1px solid {NTH_BORDER};"
        ):
            ui.label("Submit Transcription Job").classes("text-lg font-bold").style(
                f"color: {NTH_TEXT_PRIMARY};"
            )

            self._url_input = ui.input(
                label="Video Source (URL or local file path)",
                placeholder="https://youtube.com/... or C:\\path\\to\\video.mp4",
            ).classes("w-full")

            self._model_select = ui.select(
                options=["tiny", "base", "small", "medium", "large-v3"],
                value="base",
                label="Whisper Model",
            ).classes("w-full")

            self._submit_button = ui.button(
                "Transcribe", on_click=self._submit
            ).style(f"background-color: {NTH_ACCENT_BLUE}; color: white;")

            with ui.row().classes("w-full items-center gap-3 mt-2"):
                ui.label("Status:").style(f"color: {NTH_TEXT_SECOND};")
                self._status_badge = ui.label("idle").style(
                    f"color: {NTH_TEXT_SECOND}; font-weight: bold;"
                )

            self._job_id_label = ui.label("").style(
                f"color: {NTH_TEXT_SECOND}; font-family: monospace; font-size: 0.75rem;"
            )
            self._created_label = ui.label("").style(
                f"color: {NTH_TEXT_SECOND}; font-size: 0.75rem;"
            )

    # ------------------------------- actions -------------------------------

    def _submit(self) -> None:
        url = (self._url_input.value or "").strip() if self._url_input else ""
        model = self._model_select.value if self._model_select else "base"
        if not url:
            ui.notify("Please enter a video URL or local file path", type="warning")
            return

        try:
            resp = httpx.post(
                f"{self.api_base}/jobs",
                json={"url": url, "whisper_model": model},
                timeout=10.0,
            )
        except Exception as e:
            ui.notify(f"API request failed: {e}", type="negative")
            return

        if resp.status_code != 202:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            ui.notify(f"Submission rejected ({resp.status_code}): {detail}", type="negative")
            return

        data = resp.json()
        self.current_job_id = data["job_id"]
        if self._submit_button is not None:
            self._submit_button.disable()
        if self._job_id_label is not None:
            self._job_id_label.set_text(f"job_id: {data['job_id'][:8]}…")
        if self._created_label is not None:
            self._created_label.set_text(f"created: {data['created_at']}")
        self._update_status_badge(data["status"])

        # Poll via ui.timer so updates run in the client context and reach the browser.
        self._polling_active = True
        self._poll_timer = ui.timer(3.0, self._poll_once, active=True)

    async def _poll_once(self) -> None:
        if not self._polling_active or not self.current_job_id:
            return
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.api_base}/jobs/{self.current_job_id}"
                )
        except Exception:
            return
        if resp.status_code != 200:
            return
        data = resp.json()
        status = data["status"]
        self._update_status_badge(status)
        if status == "complete":
            self._stop_polling()
            if self.on_job_complete:
                try:
                    result = self.on_job_complete(self.current_job_id)
                    if hasattr(result, "__await__"):
                        await result
                except Exception as e:
                    ui.notify(f"Failed to load transcript: {e}", type="negative")
            self._reset()
        elif status == "failed":
            self._stop_polling()
            ui.notify(
                f"Job failed: {data.get('error_message') or 'unknown error'}",
                type="negative",
            )
            self._reset()

    def _stop_polling(self) -> None:
        self._polling_active = False
        if self._poll_timer is not None:
            try:
                self._poll_timer.deactivate()
            except Exception:
                pass
            self._poll_timer = None

    def _update_status_badge(self, status: str) -> None:
        color = status_color(status)
        if self._status_badge is not None:
            self._status_badge.set_text(status)
            self._status_badge.style(f"color: {color}; font-weight: bold;")

    def _reset(self) -> None:
        if self._submit_button is not None:
            self._submit_button.enable()
