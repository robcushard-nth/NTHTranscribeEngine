# NTH Transcript Engine

A local, end-to-end transcription pipeline. Paste a **YouTube URL, Vimeo URL, direct video URL, or local file path** (video or audio), pick a Whisper model, and get back a structured, timestamped transcript you can browse, copy, and export as TXT, SRT, JSON, or DOCX. All transcription runs locally via [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) — no third-party API calls, no data leaves your machine.

Built by NTH AI Dynamics as a five-sprint delivery:

- **Sprint 1** — Foundation: data models, YouTube ingestion, FFmpeg audio extraction, Whisper engine
- **Sprint 2** — API: SQLite persistence + FastAPI REST layer with background job processing
- **Sprint 3** — UI: NiceGUI dashboard with submission, history, and viewer panels
- **Sprint 4** — Exports: TXT / SRT / JSON / DOCX export engine and history browsing
- **Sprint 5** — Multi-source ingestion: local files, direct video URLs, Vimeo — auto-detected from the submitted source string

---

## Table of Contents

1. [Architecture](#architecture)
2. [Tech Stack](#tech-stack)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Running the App](#running-the-app)
6. [Configuration](#configuration)
7. [Project Structure](#project-structure)
8. [REST API Reference](#rest-api-reference)
9. [Database Schema](#database-schema)
10. [Testing](#testing)
11. [Troubleshooting](#troubleshooting)
12. [User Guide](USER_GUIDE.md)

---

## Architecture

```
                       ┌────────────────────────┐
                       │   Browser (localhost)  │
                       └───────────┬────────────┘
                                   │ HTTP
                       ┌───────────▼────────────┐
                       │   NiceGUI Dashboard    │  ui/app.py  (port 8080, configurable)
                       │  submit | history | viewer
                       └───────────┬────────────┘
                                   │ httpx (REST)
                       ┌───────────▼────────────┐
                       │   FastAPI REST API     │  api/main.py (port 8000)
                       │   /jobs  /exports       │
                       │   source-type detector  │
                       └───────────┬────────────┘
                                   │
               ┌───────────────────┼──────────────────┐
               │                   │                  │
       ┌───────▼─────┐     ┌───────▼──────┐    ┌──────▼──────┐
       │ JobProcessor│     │ Repository    │    │  Exports    │
       │ (daemon)    │     │ (SQLite)      │    │ txt/srt/    │
       └───────┬─────┘     └───────────────┘    │ json/docx   │
               │                                 └─────────────┘
    ┌──────────┼──────────┬──────────┬───────────┐
    │          │          │          │           │
┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼─────┐
│YouTube │ │ Vimeo  │ │Direct  │ │ Local  │ │ FFmpeg  │ → faster-whisper → SQLite
│yt-dlp  │ │yt-dlp  │ │URL     │ │ file   │ │ 16 kHz  │
│        │ │        │ │httpx   │ │ copy   │ │ mono WAV│
└────────┘ └────────┘ └────────┘ └────────┘ └─────────┘
```

**Flow:**
1. User submits a **source string** (YouTube URL, Vimeo URL, direct video URL, or local file path) + model choice in the UI.
2. API's `_detect_source_type()` walks four validators in priority order and dispatches to the matching handler.
3. API creates a job row in SQLite and returns a `job_id` immediately (HTTP 202).
4. A daemon thread runs the pipeline: fetch (download or copy) → extract audio → transcribe → persist transcript.
5. UI polls `GET /jobs/{id}` until status is `complete`, then loads the transcript and enables exports.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| YouTube / Vimeo ingestion | yt-dlp |
| Direct URL ingestion | httpx (streamed download) |
| Local file ingestion | `shutil.copy2` (in-process) |
| Audio extraction | FFmpeg 6.x (external binary) |
| Transcription | faster-whisper (local Whisper models) |
| REST API | FastAPI + uvicorn |
| UI | NiceGUI |
| HTTP client | httpx |
| Storage | SQLite 3 |
| DOCX export | python-docx |
| Tests | pytest, pytest-mock, pytest-asyncio |

Pinned dependencies live in [requirements.txt](requirements.txt).

---

## Prerequisites

1. **Python 3.11+** on PATH.
2. **FFmpeg 6.x** on PATH. Verify with `ffmpeg -version`.
   - Windows (Chocolatey): `choco install ffmpeg`
   - macOS (Homebrew): `brew install ffmpeg`
   - Linux (Debian/Ubuntu): `sudo apt-get install ffmpeg`
3. **Network access** — required for YouTube, Vimeo, and direct video URL ingestion (yt-dlp and httpx need to reach the source). **Not required for local file ingestion** — those run fully offline. Transcription itself is always local.
4. **Disk space** — fetched / copied video/audio is staged under `downloads/{job_id}/` during processing. Plan for roughly 2–3× the source file size in temp storage.

---

## Installation

```bash
# 1. Move into the project
cd C:\Users\RobCushard\NTHTranscribeEngine

# 2. Create and activate a virtual environment
python -m venv venv
# Windows (bash):
source venv/Scripts/activate
# Windows (PowerShell):
# venv\Scripts\Activate.ps1
# macOS/Linux:
# source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify FFmpeg is reachable
ffmpeg -version

# 5. Copy environment config
cp .env.example .env    # (on Windows bash) or: copy .env.example .env

# 6. Run the test suite to confirm the install is healthy
pytest tests/ -v
```

---

## Running the App

The app runs as **two processes**: the API server and the UI server. You need both.

### Terminal 1 — API server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

- Initializes the SQLite repository and background `JobProcessor`.
- Serves REST endpoints at `http://localhost:8000`.
- Interactive API docs available at `http://localhost:8000/docs` (FastAPI/Swagger UI).

### Terminal 2 — UI dashboard

```bash
python -m ui.app
```

- Launches the NiceGUI dashboard at `http://localhost:8080`.
- Reads `API_BASE_URL` from `.env` (defaults to `http://localhost:8000`).
- Run it as a module (`-m ui.app`) from the project root so the absolute `from ui.colors import ...` imports in [ui/app.py](ui/app.py) resolve. `python ui/app.py` will fail with `ModuleNotFoundError: No module named 'ui'`.

Open [http://localhost:8080](http://localhost:8080) in a browser and you're live.

> First transcription run: faster-whisper downloads the chosen Whisper model weights the first time they're used (e.g. `base` is ~150 MB, `large-v3` is ~3 GB). This is a one-time cost per model.

---

## Configuration

Copy [.env.example](.env.example) to `.env` and adjust as needed. Current keys:

| Key | Default | Purpose |
|---|---|---|
| `WHISPER_MODEL` | `base` | Default Whisper model size. Options: `tiny`, `base`, `small`, `medium`, `large-v3`. |
| `WHISPER_DEVICE` | `cpu` | Inference device. Use `cuda` if you have a supported NVIDIA GPU. |
| `WHISPER_COMPUTE_TYPE` | `int8` | Quantization. `int8` (CPU), `float16` (GPU), `float32` (max precision). |
| `DOWNLOAD_DIR` | `./downloads` | Temp dir for downloaded video/audio. |
| `DB_PATH` | `./nth_transcripts.db` | SQLite database path. |
| `LOG_LEVEL` | `INFO` | Standard Python logging level. |

The UI also reads `API_BASE_URL` (defaults to `http://localhost:8000`) and `UI_PORT` (defaults to `8080`) if present in the environment.

### Picking a Whisper model

| Model | Approx size | Speed (CPU) | Quality |
|---|---|---|---|
| `tiny` | ~75 MB | Fastest | Low |
| `base` | ~150 MB | Fast | Decent for clean audio |
| `small` | ~500 MB | Moderate | Good general-purpose |
| `medium` | ~1.5 GB | Slow on CPU | Strong |
| `large-v3` | ~3 GB | Slow on CPU, usable on GPU | Best |

For quick drafts and clear podcast-style audio, `base` is a good default. For noisy audio, accents, or domain terminology, go to `small` or higher.

---

## Project Structure

```
NTHTranscribeEngine/
├── api/                          # FastAPI REST layer
│   ├── main.py                   # App + lifespan (repo + processor init)
│   ├── job_processor.py          # Background daemon pipeline — dispatches per source_type
│   ├── middleware/cors.py
│   └── routes/
│       ├── jobs.py               # POST/GET /jobs + _detect_source_type() dispatcher
│       └── exports.py            # /jobs/{id}/transcript/export?format=...
├── ui/                           # NiceGUI dashboard
│   ├── app.py                    # Entry point — `python -m ui.app` (from project root)
│   ├── colors.py                 # NTH dark-theme palette
│   └── panels/
│       ├── job_submission_panel.py
│       ├── history_panel.py
│       └── transcript_viewer_panel.py
├── ingestion/                    # Source handlers — one per SourceType
│   ├── youtube_handler.py        # yt-dlp + YouTube URL validation
│   ├── vimeo_handler.py          # yt-dlp + Vimeo URL validation
│   ├── url_handler.py            # httpx stream-download for direct video URLs
│   └── local_file_handler.py     # shutil copy + Unicode-clean path validation
├── transcription/                # Audio-to-text pipeline
│   ├── audio_extractor.py        # FFmpeg → 16 kHz mono WAV
│   └── engine.py                 # faster-whisper wrapper
├── storage/
│   └── repository.py             # Thread-safe SQLite repository
├── exports/                      # Pure-function formatters
│   ├── txt_exporter.py
│   ├── srt_exporter.py
│   ├── json_exporter.py
│   └── docx_exporter.py
├── models/
│   └── transcript.py             # Frozen dataclasses + enums (SourceType, JobStatus, ...)
├── tests/                        # Sprint-aligned pytest suites (test_sprint1..5)
├── .claude/agents/               # Per-sprint master docs + four-agent specs
├── .gitignore                    # Excludes venv/, __pycache__/, downloads/, .env, *.db
├── downloads/                    # Staging for fetched/copied media (gitignored)
├── nth_transcripts.db            # SQLite (gitignored — created on first run)
├── .env                          # Local config (gitignored)
├── .env.example                  # Committed template
├── requirements.txt
└── README.md
```

Key architectural rules:
- `models/transcript.py` is **frozen** after Sprint 1. Downstream code imports, never redefines.
- `exports/*` are pure functions: `(Transcript) -> bytes|str`. No I/O.
- Repository is the only module that talks to SQLite; API + JobProcessor go through it.
- Source-type validators are stateless (`__new__` without `__init__`) so the API-layer dispatcher in [api/routes/jobs.py](api/routes/jobs.py) can detect type without touching disk.
- Prior-sprint files are frozen unless explicitly listed on a Sprint's allowlist; the QA Agent verifies via `git diff` before commit.

---

## REST API Reference

Base URL: `http://localhost:8000` — interactive docs at `/docs`.

### Submit a job

The `url` field name is kept for backward compatibility but accepts any of four source forms — the API auto-detects which:

| Source | Example value |
|---|---|
| YouTube | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| Vimeo | `https://vimeo.com/123456` |
| Direct video URL | `https://example.com/clip.mp4` |
| Local file path | `C:\Users\You\Videos\meeting.mp4` (or `.mp3`, `.wav`, `.m4a`, etc.) |

```http
POST /jobs
Content-Type: application/json

{
  "url": "C:\\Users\\You\\Videos\\meeting.mp4",
  "whisper_model": "base"
}
```

**Response 202:**
```json
{
  "job_id": "a1b2c3...",
  "status": "pending",
  "source_url": "C:\\Users\\You\\Videos\\meeting.mp4",
  "whisper_model": "base",
  "created_at": "2026-04-27T21:16:37Z"
}
```

A garbage source returns **400 Bad Request** with `"Unrecognized source. Provide a YouTube URL, Vimeo URL, direct video URL ending in a media extension, or a local file path."`

### List jobs

```http
GET /jobs
```
Returns all jobs, newest first.

### Get job status

```http
GET /jobs/{job_id}
```
Status values: `pending` → `downloading` → `extracting` → `transcribing` → `complete` (or `failed`).

### Get transcript

```http
GET /jobs/{job_id}/transcript
```
Returns full transcript with segments. Responds **409 Conflict** if the job is not yet `complete`.

### Export transcript

```http
GET /jobs/{job_id}/transcript/export?format={txt|srt|json|docx}
```
Returns the file as a download with the appropriate `Content-Type` and `Content-Disposition` headers.

### cURL cheat sheet

```bash
# Submit — YouTube
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","whisper_model":"base"}'

# Submit — Vimeo
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"url":"https://vimeo.com/123456","whisper_model":"base"}'

# Submit — direct video URL
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/clip.mp4","whisper_model":"base"}'

# Submit — local file (backslashes must be JSON-escaped)
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"url":"C:\\Users\\You\\Videos\\meeting.mp4","whisper_model":"base"}'

# Poll
curl http://localhost:8000/jobs/<job_id>

# Fetch transcript
curl http://localhost:8000/jobs/<job_id>/transcript

# Download SRT
curl -OJ "http://localhost:8000/jobs/<job_id>/transcript/export?format=srt"
```

---

## Database Schema

SQLite file: `nth_transcripts.db` (path configurable via `DB_PATH`).

**`jobs`** — one row per submission:

| Column | Type | Notes |
|---|---|---|
| `job_id` | TEXT PK | UUID |
| `source_url` | TEXT | Input URL |
| `source_type` | TEXT | `youtube`, `vimeo`, `direct_url`, `local_file` |
| `whisper_model` | TEXT | Requested model |
| `status` | TEXT | State machine value |
| `created_at` | TEXT | ISO 8601 |
| `completed_at` | TEXT | ISO 8601 or NULL |
| `error_message` | TEXT | Populated on failure |
| `audio_file_path` | TEXT | Path to extracted WAV |
| `video_file_path` | TEXT | Path to downloaded video |

**`transcripts`** — one row per completed transcription:

| Column | Type | Notes |
|---|---|---|
| `transcript_id` | TEXT PK | UUID |
| `job_id` | TEXT FK | References `jobs.job_id` |
| `full_text` | TEXT | Concatenated segment text |
| `language_detected` | TEXT | e.g. `en` |
| `whisper_model_used` | TEXT | Actual model used |
| `segment_count` | INTEGER | |
| `word_count` | INTEGER | |
| `processing_duration_seconds` | REAL | Wall-clock transcription time |
| `created_at` | TEXT | ISO 8601 |
| `segments_json` | TEXT | JSON array of `{segment_id, start_time, end_time, text, confidence}` |

Writes are serialized through a `threading.RLock` in the repository to stay safe with the daemon job thread.

---

## Testing

Run everything:

```bash
pytest tests/ -v
```

Per sprint:

```bash
pytest tests/test_sprint1_foundation.py -v   # models, ingestion, transcription
pytest tests/test_sprint2_api.py -v          # repository + API endpoints
pytest tests/test_sprint3_ui.py -v           # UI panel logic
pytest tests/test_sprint4_exports.py -v      # export formatters
pytest tests/test_sprint5_multi_source.py -v # local file / direct URL / Vimeo + dispatcher
```

Tests rely on `pytest-mock` for external dependencies (yt-dlp, FFmpeg, Whisper, network), so they run offline and quickly. Full suite: **77 tests** across the five sprint files.

---

## Troubleshooting

**`FFmpeg not found` on job start.**
Install FFmpeg and ensure `ffmpeg` resolves on PATH. Restart the API terminal after installing.

**Job stuck in `pending`.**
The API server owns the daemon processor. If you restart the API, in-flight jobs are orphaned — resubmit the URL.

**`409 Conflict` from `/jobs/{id}/transcript`.**
The job isn't `complete` yet. Poll `GET /jobs/{id}` until `status == "complete"`.

**First run is slow.**
faster-whisper downloads model weights on first use. Watch the API terminal — subsequent runs use the cached model.

**CUDA errors with `WHISPER_DEVICE=cuda`.**
Fall back to `cpu` + `int8` to confirm the rest of the pipeline works, then debug the CUDA/cuDNN install separately.

**UI shows "Failed to reach API".**
Confirm the API is running at the URL in `API_BASE_URL` (default `http://localhost:8000`) and that nothing else is bound to port 8000.

**YouTube download fails with extractor errors.**
Upgrade yt-dlp — YouTube changes break it periodically: `pip install -U yt-dlp`. The same applies if a Vimeo extractor breaks.

**Direct URL job fails with `Invalid direct video URL`.**
The validator requires `http(s)://` and a path ending in a known media extension (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.flv`, `.mp3`, `.wav`, `.m4a`). HTML pages, query-string-disguised media, and pre-signed S3 URLs with no extension are rejected — point to the actual file, not an embed page.

**Local file job fails with `Invalid local file path` despite the file existing.**
Likely a Windows Explorer "Copy as path" artifact — the clipboard text starts with an invisible `U+202A` (Left-to-Right Embedding) character. The [LocalFileHandler](ingestion/local_file_handler.py) strips Cf-category Unicode chars and wrapping quotes, but if you're hitting this from a different OS-level paste tool, retype the path manually.

**Port 8080 already in use when starting the UI.**
Set `UI_PORT` in `.env` (e.g. `UI_PORT=8090`) and reopen the browser at the new port. The default `0.0.0.0` bind is also a candidate for tightening — consider running on `127.0.0.1` only if your host is multi-user.

**Port 8000 already in use when starting the API.**
Pass `--port 8001` (or any free port) and update `API_BASE_URL` in `.env` so the UI talks to the new port.

---

## License & Ownership

Internal tool — NTH AI Dynamics / NTH Simple Solution Corp.

For an end-user walkthrough (submitting jobs, reading the viewer, exporting), see [USER_GUIDE.md](USER_GUIDE.md).
