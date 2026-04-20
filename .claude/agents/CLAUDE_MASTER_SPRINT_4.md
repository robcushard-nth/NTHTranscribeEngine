# CLAUDE_MASTER_SPRINT_4.md
**Project:** NTH Transcript Engine
**Sprint:** 4 — Export Engine + History Panel
**Module:** TXT/SRT/JSON/DOCX Exporters · Export API · Transcript History Panel
**Author:** William "Rob" Cushard — NTH AI Dynamics
**Git Author:** `robcushard-nth <rob.cushard@nthsimplesolution.com>`
**Repo:** `C:\Users\RobCushard\NTHTranscribeEngine\`
**Agent Path:** `.claude\agents\`
**Date:** 2026-04-09
**Status:** 🔴 NOT STARTED — Requires Sprint 3 COMPLETE

---

## Sprint Mission

Sprint 4 closes the loop on the operator workflow. After Sprint 3 the user can
transcribe a YouTube video and read it in the browser, but they cannot export
the transcript to a file or browse anything they ran earlier. Sprint 4 delivers
both:

1. **Export Engine** — pure, dependency-light formatters that turn a `Transcript`
   object into TXT, SRT, JSON, or DOCX bytes; a new FastAPI endpoint that
   serves those bytes as a file download; and export buttons in the viewer panel.
2. **History Panel** — a third NiceGUI panel that lists every prior job (newest
   first) and, on click, loads that job's transcript into the existing viewer
   panel. Backed by the existing `GET /jobs` and `GET /jobs/{id}/transcript`
   endpoints — no new persistence work.

After Sprint 4, an operator can submit a job, browse history, click any past
transcript, and download it as TXT/SRT/JSON/DOCX with one click — all without
leaving the dashboard.

> **Roadmap reshuffle:** Multi-Source ingestion (local file, direct URL, Vimeo)
> originally scoped for Sprint 4 is deferred to Sprint 5. The original Sprint 5
> Export Engine is pulled forward into this sprint and bundled with the History
> Panel that was deferred during Sprint 3 manual verification.

---

## Scope Boundary

### IN SCOPE — Sprint 4
- `exports/__init__.py`
- `exports/txt_exporter.py` — plain text + segment timestamps
- `exports/srt_exporter.py` — SubRip subtitle format
- `exports/json_exporter.py` — full structured JSON
- `exports/docx_exporter.py` — Word document via python-docx
- `api/routes/exports.py` — `GET /jobs/{job_id}/transcript/export?format={fmt}`
- `ui/panels/history_panel.py` — `HistoryPanel` class
- `tests/test_sprint4_exports.py` — QA agent writes this
- Minimum 14 pytest tests
- `requirements.txt` updated (append `python-dotenv` already present; append `python-docx`)

### Permitted modifications to frozen files (explicit allowlist)
| File | Frozen Since | Permitted Modification |
|---|---|---|
| `requirements.txt` | — | Append `python-docx>=1.1.0` |
| `api/main.py` | Sprint 2 | Add `app.include_router(exports.router, ...)` line only |
| `ui/app.py` | Sprint 3 | Add `HistoryPanel` import + render in dashboard layout |
| `ui/panels/transcript_viewer_panel.py` | Sprint 3 | Add export-buttons row (TXT/SRT/JSON/DOCX) + handlers |

No other Sprint 1, 2, or 3 file may be modified. The `models/transcript.py`
freeze remains absolute.

### OUT OF SCOPE — Sprint 4
- Local file upload, direct URL, Vimeo ingestion (Sprint 5)
- Authentication, API keys, JWT (post-roadmap)
- Cleanup of `downloads/{job_id}/` artifacts (post-roadmap)
- Dark/light mode toggle (post-roadmap)
- Server-side export caching (not needed — exports are cheap)
- PDF export (out of scope; DOCX covers the rich-text use case)

---

## Frozen Assets — Sprint 4 Must Not Modify

| File | Frozen Since |
|---|---|
| `models/transcript.py` | Sprint 1 |
| `ingestion/youtube_handler.py` | Sprint 1 |
| `transcription/audio_extractor.py` | Sprint 1 |
| `transcription/engine.py` | Sprint 1 |
| `storage/repository.py` | Sprint 2 |
| `api/job_processor.py` | Sprint 2 |
| `api/routes/jobs.py` | Sprint 2 |
| `api/middleware/cors.py` | Sprint 2 |
| `ui/colors.py` | Sprint 3 |
| `ui/panels/job_submission_panel.py` | Sprint 3 |
| `tests/test_sprint1_foundation.py` | Sprint 1 |
| `tests/test_sprint2_api.py` | Sprint 2 |
| `tests/test_sprint3_ui.py` | Sprint 3 |

QA Agent verifies via `git diff --name-only` that no file outside the explicit
allowlist appears in the diff.

---

## Module Specifications

### Module 1: `exports/txt_exporter.py`

**Responsibility:** Render a `Transcript` as plain text with timestamped
segments. No external dependencies.

```python
from models.transcript import Transcript

def export_txt(transcript: Transcript) -> str:
    """Returns a UTF-8 string. Format:
    [HH:MM:SS] segment text
    [HH:MM:SS] segment text
    ...
    """
```

Implementation rules:
- One segment per line, prefixed with `[formatted_start]` then a single space
- Header lines (optional): `# Transcript {transcript_id}` and `# Words: {word_count}`
- Trailing newline at end of output

---

### Module 2: `exports/srt_exporter.py`

**Responsibility:** Render a `Transcript` as a SubRip (`.srt`) subtitle file.

```python
def export_srt(transcript: Transcript) -> str:
    """Returns SRT-formatted string. Format per segment:
    {index}
    HH:MM:SS,mmm --> HH:MM:SS,mmm
    text

    """
```

Implementation rules:
- Index starts at 1 (not 0)
- Time format: `HH:MM:SS,mmm` with comma decimal separator (SRT standard)
- Blank line between segments
- Convert `start_time` / `end_time` floats to `HH:MM:SS,mmm` via integer math
  (no `datetime.strftime` — millisecond precision required)

---

### Module 3: `exports/json_exporter.py`

**Responsibility:** Render a `Transcript` as a structured JSON document
suitable for downstream pipelines.

```python
def export_json(transcript: Transcript) -> str:
    """Returns JSON string with full transcript + segments + metadata."""
```

Implementation rules:
- Top-level keys: `transcript_id`, `job_id`, `full_text`, `language_detected`,
  `whisper_model_used`, `segment_count`, `word_count`,
  `processing_duration_seconds`, `created_at`, `segments`
- Each segment dict: `segment_id`, `start_time`, `end_time`, `formatted_start`,
  `formatted_end`, `text`, `confidence`
- Use `json.dumps(..., indent=2, ensure_ascii=False)`

---

### Module 4: `exports/docx_exporter.py`

**Responsibility:** Render a `Transcript` as a Word document (`.docx`).
Uses the `python-docx` library.

```python
def export_docx(transcript: Transcript) -> bytes:
    """Returns docx file bytes. Layout:
    - Title: "Transcript"
    - Subtitle line: language, model, word count, segment count
    - For each segment: bold timestamp + plain text
    """
```

Implementation rules:
- Use `docx.Document()`
- Save to `io.BytesIO()` and return `.getvalue()`
- Title via `add_heading(level=1)`
- Each segment as a paragraph with two runs: bold `[HH:MM:SS]` + space + text

---

### Module 5: `api/routes/exports.py`

**Responsibility:** Single endpoint that returns the transcript in the
requested format as a file download.

```
GET /jobs/{job_id}/transcript/export?format={txt|srt|json|docx}
```

**Behavior:**
- 404 if job not found
- 409 if job not COMPLETE
- 404 if no transcript stored
- 400 if format is missing or unknown
- 200 with `Response`, correct `media_type`, and
  `Content-Disposition: attachment; filename="transcript_{job_id_short}.{ext}"`

**Format → media type → extension table:**
| format | media_type | extension |
|---|---|---|
| `txt`  | `text/plain; charset=utf-8` | `.txt` |
| `srt`  | `application/x-subrip; charset=utf-8` | `.srt` |
| `json` | `application/json; charset=utf-8` | `.json` |
| `docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.docx` |

The route is mounted in `api/main.py`:
```python
from api.routes import exports
app.include_router(exports.router, prefix="/jobs", tags=["exports"])
```

---

### Module 6: `ui/panels/history_panel.py`

**Responsibility:** Browse past jobs. Click a row to load that job's transcript
into the existing viewer panel.

**Required UI sections:**
1. **Header row** — "History" label + Refresh button (right-aligned)
2. **Job list** — scrollable, each row shows:
   - Status badge (small colored dot using `status_color()` from submission panel)
   - Truncated job_id (first 8 chars, monospace)
   - Source URL (truncated to ~40 chars)
   - Created timestamp (just `HH:MM` if today, else `MM-DD HH:MM`)
3. **Empty state** — "No jobs yet" when list is empty

**Class interface:**
```python
class HistoryPanel:
    def __init__(self, api_base: str):
        self.api_base = api_base
        self.on_select: Optional[Callable[[str], Awaitable[None]]] = None
        self._list_container = None

    def render(self) -> None: ...
    async def refresh(self) -> None:
        """GET /jobs and rebuild the list."""
    async def _on_row_click(self, job_id: str) -> None:
        """If on_select is set, await on_select(job_id)."""
```

**Wiring in `ui/app.py`** (permitted modification):
- Three-column layout: submission (1/4) | history (1/4) | viewer (1/2)
- `history_panel.on_select = viewer_panel.load_transcript`
- Call `await history_panel.refresh()` once at dashboard build time
- Submission panel's `on_job_complete` should also trigger `history_panel.refresh()`
  after loading the new transcript

---

### Module 7: Viewer panel additions (permitted modification)

In `ui/panels/transcript_viewer_panel.py`, add an export-buttons row inside
the existing card, between the header row and the video info card:

```python
with ui.row().classes("w-full gap-2"):
    ui.button("TXT",  on_click=lambda: self._download("txt")).props("dense")
    ui.button("SRT",  on_click=lambda: self._download("srt")).props("dense")
    ui.button("JSON", on_click=lambda: self._download("json")).props("dense")
    ui.button("DOCX", on_click=lambda: self._download("docx")).props("dense")
```

`self._download(fmt)` opens the export URL via `ui.download(...)` or `ui.open(...)`
pointing at `{api_base}/jobs/{current_job_id}/transcript/export?format={fmt}`.
Buttons are disabled until a transcript is loaded.

The viewer panel must remember the current `job_id` (store it in
`load_transcript` before fetching).

---

## Updated requirements.txt (Full — Sprints 1–4)

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
python-docx>=1.1.0
```

---

## Directory Structure After Sprint 4

```
NTH_TRANSCRIPT_ENGINE/
├── CLAUDE_MASTER_SPRINT_4.md          ← This file
├── models/                            ← FROZEN
├── ingestion/                         ← FROZEN
├── transcription/                     ← FROZEN
├── storage/                           ← FROZEN
├── api/
│   ├── main.py                        ← MODIFIED (one new include_router line)
│   ├── job_processor.py               ← FROZEN
│   ├── routes/
│   │   ├── jobs.py                    ← FROZEN
│   │   └── exports.py                 ← NEW (Sprint 4)
│   └── middleware/                    ← FROZEN
├── exports/
│   ├── __init__.py                    ← NEW (Sprint 4)
│   ├── txt_exporter.py                ← NEW (Sprint 4)
│   ├── srt_exporter.py                ← NEW (Sprint 4)
│   ├── json_exporter.py               ← NEW (Sprint 4)
│   └── docx_exporter.py               ← NEW (Sprint 4)
├── ui/
│   ├── app.py                         ← MODIFIED (mount HistoryPanel)
│   ├── colors.py                      ← FROZEN
│   └── panels/
│       ├── job_submission_panel.py    ← FROZEN
│       ├── transcript_viewer_panel.py ← MODIFIED (add export buttons)
│       └── history_panel.py           ← NEW (Sprint 4)
├── tests/
│   ├── test_sprint1_foundation.py     ← FROZEN
│   ├── test_sprint2_api.py            ← FROZEN
│   ├── test_sprint3_ui.py             ← FROZEN
│   └── test_sprint4_exports.py        ← NEW (Sprint 4) — QA agent writes
└── requirements.txt                   ← MODIFIED (append python-docx)
```

---

## Test Requirements — Sprint 4

**Minimum tests:** 14
**Test file:** `tests/test_sprint4_exports.py`
**Written by:** QA Agent only

| # | Test Name | What It Validates |
|---|---|---|
| 1 | `test_export_txt_basic` | TXT exporter returns one line per segment with `[HH:MM:SS]` prefix |
| 2 | `test_export_txt_word_count_header` | TXT header reflects transcript word count |
| 3 | `test_export_srt_format` | SRT output starts with `1\n00:00:00,000 --> ...` |
| 4 | `test_export_srt_indexing` | SRT segment indices increment from 1 |
| 5 | `test_export_srt_millisecond_precision` | SRT timestamps use comma decimal + ms precision |
| 6 | `test_export_json_round_trip` | JSON parses back into a dict with all expected keys |
| 7 | `test_export_json_segments_complete` | JSON segments include all fields incl. confidence |
| 8 | `test_export_docx_returns_bytes` | DOCX exporter returns non-empty bytes starting with PK header |
| 9 | `test_api_export_txt` | `GET /jobs/{id}/transcript/export?format=txt` returns 200 + text/plain |
| 10 | `test_api_export_srt` | format=srt returns 200 + application/x-subrip |
| 11 | `test_api_export_json` | format=json returns 200 + application/json |
| 12 | `test_api_export_docx` | format=docx returns 200 + docx media type |
| 13 | `test_api_export_invalid_format` | format=pdf returns 400 |
| 14 | `test_api_export_not_complete` | Export on non-complete job returns 409 |
| 15 | `test_api_export_job_not_found` | Export on missing job returns 404 |
| 16 | `test_history_panel_init` | HistoryPanel constructs with api_base, no jobs |
| 17 | `test_history_panel_refresh_calls_api` | refresh() hits `GET /jobs` (mocked) |
| 18 | `test_sprint1_2_3_regression` | All prior-sprint imports remain clean |

**Hard Gate Tests:**
- `test_export_srt_millisecond_precision` — format correctness
- `test_api_export_txt` — end-to-end API path
- `test_api_export_docx` — binary path + python-docx integration

---

## Definition of Done — Sprint 4

- [ ] Sprint 1+2+3 regression: `pytest tests/test_sprint1_foundation.py tests/test_sprint2_api.py tests/test_sprint3_ui.py -v` — all 41 pass
- [ ] `exports/__init__.py` delivered
- [ ] `exports/txt_exporter.py` — `export_txt` importable
- [ ] `exports/srt_exporter.py` — `export_srt` importable
- [ ] `exports/json_exporter.py` — `export_json` importable
- [ ] `exports/docx_exporter.py` — `export_docx` importable, returns bytes
- [ ] `api/routes/exports.py` — router with one endpoint, four formats
- [ ] `api/main.py` — exports router mounted (one-line addition)
- [ ] `ui/panels/history_panel.py` — `HistoryPanel` importable
- [ ] `ui/app.py` — three-column layout, history wired to viewer
- [ ] `ui/panels/transcript_viewer_panel.py` — four export buttons added, disabled when empty
- [ ] `requirements.txt` — `python-docx>=1.1.0` appended
- [ ] `tests/test_sprint4_exports.py` — minimum 14 tests
- [ ] Sprint 4 tests pass
- [ ] Full suite passes: `pytest tests/ -v` (55+ total expected)
- [ ] Hard gate tests PASS
- [ ] `git diff --name-only` shows only allowlisted modifications + new files
- [ ] Manual: launch UI, click any past job in History, see transcript load
- [ ] Manual: click TXT/SRT/JSON/DOCX buttons, verify file downloads and opens correctly
- [ ] git commit: `sprint4: export engine + history panel complete`

---

## PM Agent Launch Prompt

```
You are the PM Agent for Sprint 4 of the NTH Transcript Engine.

Read CLAUDE_MASTER_SPRINT_4.md completely before taking any action.

Sprints 1, 2, and 3 are complete. Your FIRST action is to run the full
prior-sprint regression before any Sprint 4 code is written:

  pytest tests/test_sprint1_foundation.py tests/test_sprint2_api.py tests/test_sprint3_ui.py -v

All 41 tests must pass. Any failure — halt and report to user.

Execute in this sequence:
1. Sprints 1+2+3 regression (gate)
2. Backend Agent Phase 4a: exports/ package — txt, srt, json, docx exporters
3. Backend Agent Phase 4b: api/routes/exports.py
4. Backend Agent Phase 4c: append python-docx to requirements.txt and pip install
5. Backend Agent Phase 4d: ALLOWLISTED modification — add include_router line to api/main.py
6. Frontend Agent Phase 4e: ui/panels/history_panel.py
7. Frontend Agent Phase 4f: ALLOWLISTED modification — add export buttons + _download to ui/panels/transcript_viewer_panel.py
8. Frontend Agent Phase 4g: ALLOWLISTED modification — add HistoryPanel to three-column layout in ui/app.py
9. Import verification for all new and modified modules
10. QA Gate 1: hard gate tests (srt precision + api export txt + api export docx)
11. QA Gate 2: full suite — pytest tests/ -v
12. Verify diff: only allowlisted files modified, all other frozen files untouched
13. DoD report — explicit PASS/FAIL every item
14. Manual verification checklist printed for the user (history click + four download buttons)
15. git commit: sprint4: export engine + history panel complete

Critical constraints:
- models/transcript.py is frozen forever — never modify
- Only the four files in the Permitted File Modifications table may be edited;
  all other prior-sprint files including test files are frozen
- Exporters are pure functions taking a Transcript and returning str/bytes —
  they must NOT call the API, the repository, or perform any I/O beyond
  in-memory string/byte construction
- The export endpoint loads transcripts via the existing TranscriptRepository;
  it must not duplicate persistence logic
- HistoryPanel and the export buttons call FastAPI endpoints via httpx only;
  no direct imports from ingestion/, transcription/, storage/, or exports/
```
