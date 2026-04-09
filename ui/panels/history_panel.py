"""
NTH Transcript Engine — History Panel
Sprint 4 | Owner: Frontend Agent

Lists past jobs (newest first) and on click loads them into the viewer panel.
Calls the FastAPI /jobs endpoint via httpx only — no direct repository access.
"""

from datetime import datetime
from typing import Awaitable, Callable, Optional

import httpx
from nicegui import ui

from ui.colors import (
    NTH_ACCENT_AMBER,
    NTH_ACCENT_BLUE,
    NTH_ACCENT_GREEN,
    NTH_ACCENT_RED,
    NTH_BORDER,
    NTH_CARD_BG,
    NTH_HOVER,
    NTH_TEXT_PRIMARY,
    NTH_TEXT_SECOND,
)


_IN_PROGRESS = {"pending", "downloading", "extracting", "transcribing"}


def _status_dot_color(status: str) -> str:
    if status == "complete":
        return NTH_ACCENT_GREEN
    if status == "failed":
        return NTH_ACCENT_RED
    if status in _IN_PROGRESS:
        return NTH_ACCENT_AMBER
    return NTH_TEXT_SECOND


def _format_when(iso_ts: str) -> str:
    """Render an ISO timestamp as 'HH:MM' if today, else 'MM-DD HH:MM'."""
    try:
        dt = datetime.fromisoformat(iso_ts)
    except Exception:
        return iso_ts
    today = datetime.utcnow().date()
    if dt.date() == today:
        return dt.strftime("%H:%M")
    return dt.strftime("%m-%d %H:%M")


class HistoryPanel:
    def __init__(self, api_base: str):
        self.api_base = api_base
        self.on_select: Optional[Callable[[str], Awaitable[None]]] = None
        self._jobs: list[dict] = []
        self._list_container = None
        self._empty_label = None

    def render(self) -> None:
        with ui.card().classes("w-full").style(
            f"background-color: {NTH_CARD_BG}; border: 1px solid {NTH_BORDER};"
        ):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("History").classes("text-lg font-bold").style(
                    f"color: {NTH_TEXT_PRIMARY};"
                )
                ui.button("Refresh", on_click=self.refresh).props("dense")

            self._list_container = ui.column().classes(
                "w-full max-h-96 overflow-auto"
            )
            with self._list_container:
                self._empty_label = ui.label("No jobs yet").style(
                    f"color: {NTH_TEXT_SECOND};"
                )

    async def refresh(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.api_base}/jobs")
        except Exception as e:
            ui.notify(f"Failed to load history: {e}", type="negative")
            return
        if resp.status_code != 200:
            ui.notify(
                f"GET /jobs returned {resp.status_code}", type="negative"
            )
            return
        self._jobs = resp.json() or []
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        if self._list_container is None:
            return
        self._list_container.clear()
        with self._list_container:
            if not self._jobs:
                ui.label("No jobs yet").style(f"color: {NTH_TEXT_SECOND};")
                return
            for job in self._jobs:
                self._render_row(job)

    def _render_row(self, job: dict) -> None:
        job_id = job.get("job_id", "")
        status = job.get("status", "")
        url = job.get("source_url", "")
        created = job.get("created_at", "")
        short = job_id[:8]
        url_short = url if len(url) <= 40 else url[:37] + "…"
        when = _format_when(created)
        color = _status_dot_color(status)

        row = ui.row().classes(
            "w-full items-center gap-2 py-2 px-2 cursor-pointer"
        ).style(f"border-bottom: 1px solid {NTH_BORDER};")
        with row:
            ui.html(
                f'<span style="display:inline-block;width:10px;height:10px;'
                f'border-radius:50%;background-color:{color};"></span>'
            )
            ui.label(short).classes("font-mono text-xs").style(
                f"color: {NTH_ACCENT_BLUE};"
            )
            ui.label(url_short).classes("text-xs flex-grow").style(
                f"color: {NTH_TEXT_PRIMARY};"
            )
            ui.label(when).classes("text-xs").style(
                f"color: {NTH_TEXT_SECOND};"
            )
        row.on("click", lambda _, jid=job_id: self._handle_click(jid))

    async def _handle_click(self, job_id: str) -> None:
        if not self.on_select:
            return
        try:
            result = self.on_select(job_id)
            if hasattr(result, "__await__"):
                await result
        except Exception as e:
            ui.notify(f"Failed to load transcript: {e}", type="negative")
