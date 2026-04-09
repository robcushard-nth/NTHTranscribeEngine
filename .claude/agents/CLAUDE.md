# CLAUDE.md — NTH Transcript Engine
**Project:** NTH Transcript Engine
**Organization:** NTH AI Dynamics | NTH Simple Solution Corp
**Author:** William "Rob" Cushard — Fractional COO / AI Operations Strategist
**Contact:** rob.cushard@nthsimplesolution.com | 470-426-4144
**Git Author:** `robcushard-nth <rob.cushard@nthsimplesolution.com>`
**Repo Root:** `C:\Users\RobCushard\NTH_TRANSCRIPT_ENGINE\`
**Status:** Active Development
**Last Updated:** 2026-04-09

---

## Mission

The NTH Transcript Engine ingests video from YouTube, local files, and direct
video URLs, extracts audio, and produces structured, human-readable transcripts
using OpenAI Whisper (via faster-whisper). It delivers a full-stack application:
Python backend, FastAPI REST layer, and NiceGUI dashboard — enabling any operator
to drop in a video source and receive a clean, exportable transcript in seconds.

This tool directly supports NTH AI Dynamics' mission of AI-enabled operational
intelligence — converting unstructured video content into structured, searchable,
exportable knowledge assets.

---

## Architecture Overview

```
NTH_TRANSCRIPT_ENGINE/
├── CLAUDE.md                          ← This file (Claude Code root context)
├── CLAUDE_MASTER_SPRINT_1.md          ← Sprint 1 spec (Foundation)
├── CLAUDE_MASTER_SPRINT_2.md          ← Sprint 2 spec (API Layer) [future]
├── CLAUDE_MASTER_SPRINT_3.md          ← Sprint 3 spec (NiceGUI Dashboard) [future]
├── CLAUDE_MASTER_SPRINT_4.md          ← Sprint 4 spec (Multi-Source) [future]
├── CLAUDE_MASTER_SPRINT_5.md          ← Sprint 5 spec (Export Engine) [future]
├── .claude/
│   └── agents/
│       ├── pm-agent.md
│       ├── backend-agent.md
│       ├── frontend-agent.md
│       └── qa-agent.md
├── models/
│   └── transcript.py                  ← Authoritative data models (Sprint 1, frozen)
├── ingestion/
│   ├── __init__.py
│   ├── youtube_handler.py             ← yt-dlp YouTube ingestion (Sprint 1)
│   ├── local_file_handler.py          ← Local video file ingestion (Sprint 4)
│   └── url_handler.py                 ← Direct URL ingestion (Sprint 4)
├── transcription/
│   ├── __init__.py
│   ├── engine.py                      ← faster-whisper transcription engine (Sprint 1)
│   └── audio_extractor.py             ← FFmpeg audio extraction (Sprint 1)
├── api/
│   ├── __init__.py
│   ├── main.py                        ← FastAPI app entry point (Sprint 2)
│   ├── routes/
│   │   ├── jobs.py                    ← Transcription job endpoints (Sprint 2)
│   │   └── transcripts.py             ← Transcript retrieval endpoints (Sprint 2)
│   └── middleware/
│       └── cors.py                    ← CORS config (Sprint 2)
├── storage/
│   ├── __init__.py
│   └── repository.py                  ← SQLite transcript repository (Sprint 2)
├── ui/
│   ├── __init__.py
│   ├── app.py                         ← NiceGUI entry point (Sprint 3)
│   └── panels/
│       ├── job_submission_panel.py    ← Source input + submit (Sprint 3)
│       └── transcript_viewer_panel.py ← Transcript display + export (Sprint 3)
├── exports/
│   ├── __init__.py
│   ├── txt_exporter.py               ← Plain text export (Sprint 5)
│   ├── srt_exporter.py               ← SRT subtitle export (Sprint 5)
│   └── json_exporter.py              ← JSON structured export (Sprint 5)
├── tests/
│   ├── test_sprint1_foundation.py     ← Sprint 1 tests
│   ├── test_sprint2_api.py            ← Sprint 2 tests [future]
│   └── test_sprint3_ui.py             ← Sprint 3 tests [future]
├── requirements.txt
├── .env.example
└── README.md
```

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.11+ | Core runtime |
| Video Download | yt-dlp | latest | YouTube + platform ingestion |
| Audio Extraction | FFmpeg | 6.x | Video-to-audio conversion |
| Transcription | faster-whisper | latest | Local Whisper model execution |
| API | FastAPI + uvicorn | latest | REST API layer |
| UI | NiceGUI | latest | Operator dashboard |
| Storage | SQLite (built-in) | — | Job + transcript persistence |
| Testing | pytest | latest | Full test suite |
| Environment | python-dotenv | latest | Config management |

---

## Sprint Roadmap

| Sprint | Module | Status | Description |
|---|---|---|---|
| 1 | Foundation | 🔴 NOT STARTED | Data models, YouTube ingestion, audio extraction, transcription engine |
| 2 | API Layer | ⬜ PENDING | FastAPI endpoints, job queue, SQLite persistence |
| 3 | NiceGUI Dashboard | ⬜ PENDING | Job submission panel, transcript viewer panel |
| 4 | Multi-Source | ⬜ PENDING | Local file, direct URL, Vimeo ingestion |
| 5 | Export Engine | ⬜ PENDING | TXT, SRT, JSON, DOCX export formats |

---

## Key Constraints — Always Enforced

1. **Frozen Asset Rule:** Prior sprint files are immutable unless explicitly listed
   in the current sprint master doc. The QA agent verifies via `git diff`.

2. **Model Ownership:** `models/transcript.py` is owned by Sprint 1. All
   subsequent modules import from it — never redefine classes.

3. **No External API Keys Required for Core Function:** Transcription runs
   locally via faster-whisper. No OpenAI API calls for the transcription engine.

4. **FFmpeg Dependency:** FFmpeg must be installed on the host machine and
   available on PATH. The backend agent verifies this at install time.

5. **Threading Safety:** All repository write operations use `threading.RLock`.

6. **Test Minimum:** Every sprint delivers at minimum 10 new pytest tests.
   QA agent writes all tests — backend agent does not write tests.

---

## Environment Configuration

Copy `.env.example` to `.env` before running.

```env
# .env.example
WHISPER_MODEL=base          # Options: tiny, base, small, medium, large-v3
WHISPER_DEVICE=cpu          # Options: cpu, cuda (if CUDA available)
WHISPER_COMPUTE_TYPE=int8   # Options: int8, float16, float32
DOWNLOAD_DIR=./downloads    # Temp directory for video/audio files
DB_PATH=./nth_transcripts.db
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

---

## Installation Sequence (New Environment)

```bash
# 1. Clone / create repo
cd C:\Users\RobCushard\NTH_TRANSCRIPT_ENGINE

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify FFmpeg
ffmpeg -version

# 5. Copy env config
copy .env.example .env

# 6. Run tests
pytest tests/ -v

# 7. Launch API (Sprint 2+)
uvicorn api.main:app --reload

# 8. Launch UI (Sprint 3+)
python ui/app.py
```

---

## Development Rules

- **Branch per sprint:** `git checkout -b sprint{N}-{module}`
- **Commit format:** `git commit -m "sprint{N}: {module} complete"`
- **No AI-generated test shortcuts:** QA agent writes real tests with real assertions
- **No mock transcription in integration tests:** Use a real audio fixture file
- **Integration tests marked:** `@pytest.mark.integration` and run separately
- **Windows paths:** Use `pathlib.Path` throughout — no hardcoded separators

---

## Agent Execution

Launch Claude Code in VS Code from the repo root. Drop the current sprint's
CLAUDE_MASTER_SPRINT_N.md into the repo root. Drop the four agent files into
`.claude\agents\`. Paste the PM Agent launch prompt from the bottom of the
master doc into Claude Code to begin execution.

The four agents operate as follows:
- **PM Agent** — reads master doc, enforces gates, owns DoD, issues git commit
- **Backend Agent** — builds models, handlers, engine in sequence
- **Frontend Agent** — builds NiceGUI panels after QA gate clears
- **QA Agent** — writes all tests, runs all gates, validates frozen assets

**Current sprint to execute: Sprint 1 — Foundation**
See `CLAUDE_MASTER_SPRINT_1.md` for full specification.
