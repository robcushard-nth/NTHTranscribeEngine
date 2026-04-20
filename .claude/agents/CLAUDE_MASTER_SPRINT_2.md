# CLAUDE_MASTER_SPRINT_2.md
**Project:** NTH Transcript Engine
**Sprint:** 2 — API Layer
**Module:** SQLite Repository · Background Job Processor · FastAPI REST Endpoints
**Author:** William "Rob" Cushard — NTH AI Dynamics
**Git Author:** `robcushard-nth <rob.cushard@nthsimplesolution.com>`
**Repo:** `C:\Users\RobCushard\NTH_TRANSCRIPT_ENGINE\`
**Agent Path:** `.claude\agents\`
**Date:** 2026-04-09
**Status:** 🔴 NOT STARTED — Requires Sprint 1 COMPLETE

---

## Sprint Mission

Sprint 2 wraps the Sprint 1 engine in a production-ready API layer. It delivers
three things: (1) a SQLite repository that persists TranscriptionJob and Transcript
objects, (2) a background job processor that runs transcription off the request
thread so the API stays non-blocking, and (3) a FastAPI application with four
REST endpoints — submit job, check status, retrieve transcript, and list all jobs.

At the end of Sprint 2, an operator posts a YouTube URL to `POST /jobs`, receives
a job_id, polls `GET /jobs/{job_id}` until status is COMPLETE, then calls
`GET /jobs/{job_id}/transcript` to retrieve the full structured transcript.
The NiceGUI UI (Sprint 3) will call these exact endpoints.

All Sprint 1 files are frozen. Sprint 2 adds new files only. The data models in
`models/transcript.py` are imported throughout — never redefined.

---

## Scope Boundary

### IN SCOPE — Sprint 2
- `storage/__init__.py`
- `storage/repository.py` — SQLite persistence for jobs and transcripts
- `api/__init__.py`
- `api/main.py` — FastAPI app entry point with lifespan
- `api/routes/__init__.py`
- `api/routes/jobs.py` — POST /jobs, GET /jobs/{id}, GET /jobs, GET /jobs/{id}/transcript
- `api/middleware/__init__.py`
- `api/middleware/cors.py` — CORS configuration
- `api/job_processor.py` — background threading job queue
- `tests/test_sprint2_api.py` — QA agent writes this
- Minimum 14 pytest tests
- `requirements.txt` updated (append FastAPI, uvicorn, httpx, pytest-asyncio)

### OUT OF SCOPE — Sprint 2
- Any NiceGUI or browser UI (Sprint 3)
- Export format endpoints: TXT, SRT, DOCX (Sprint 5)
- Authentication, API keys, JWT (post-roadmap)
- Local file upload endpoint (Sprint 4)
- Vimeo / other platform endpoints (Sprint 4)
- Celery, Redis, or any external queue (not needed — threading is sufficient)

---

## Frozen Assets — Sprint 2 Must Not Modify

| File | Frozen Since | Reason |
|---|---|---|
| `models/transcript.py` | Sprint 1 | Authoritative data models |
| `ingestion/__init__.py` | Sprint 1 | Package init |
| `ingestion/youtube_handler.py` | Sprint 1 | YouTube ingestion logic |
| `transcription/__init__.py` | Sprint 1 | Package init |
| `transcription/audio_extractor.py` | Sprint 1 | Audio extraction logic |
| `transcription/engine.py` | Sprint 1 | Whisper transcription engine |
| `tests/test_sprint1_foundation.py` | Sprint 1 | Sprint 1 regression suite |

**QA Agent verifies:** `git diff --name-only` shows zero modifications to frozen files.

---

## Permitted File Modifications — Sprint 2

| File | Modification | Reason |
|---|---|---|
| `requirements.txt` | Append 4 dependencies | Add FastAPI, uvicorn, httpx, pytest-asyncio |

---

## Authoritative Data Models — Sprint 2 API Schemas

These are Pydantic schemas for the API layer only. They live in `api/routes/jobs.py`.
They do NOT replace or modify the dataclasses in `models/transcript.py`.

```python
# api/routes/jobs.py — Pydantic schemas (define at top of file)
from pydantic import BaseModel, HttpUrl
from typing import Optional
from enum import Enum

class SubmitJobRequest(BaseModel):
    url: str
    whisper_model: Optional[str] = "base"   # tiny|base|small|medium|large-v3

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    source_url: str
    whisper_model: str
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

class SegmentResponse(BaseModel):
    segment_id: int
    start_time: float
    end_time: float
    formatted_start: str
    formatted_end: str
    text: str

class TranscriptResponse(BaseModel):
    transcript_id: str
    job_id: str
    full_text: str
    language_detected: Optional[str]
    whisper_model_used: str
    segment_count: int
    word_count: int
    processing_duration_seconds: Optional[float]
    segments: list[SegmentResponse]
    created_at: str
```

---

## Module Specifications

### Module 1: `storage/repository.py`

**Responsibility:** Persist and retrieve TranscriptionJob and Transcript objects
using SQLite. Thread-safe. In-process. No ORM — raw sqlite3.

**Tables:**
```sql
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    whisper_model TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    error_message TEXT,
    audio_file_path TEXT,
    video_file_path TEXT
);

CREATE TABLE IF NOT EXISTS transcripts (
    transcript_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    full_text TEXT NOT NULL,
    language_detected TEXT,
    whisper_model_used TEXT NOT NULL,
    segment_count INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    processing_duration_seconds REAL,
    created_at TEXT NOT NULL,
    segments_json TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);
```

**Interface:**
```python
class TranscriptRepository:
    def __init__(self, db_path: str): ...
    def _get_connection(self) -> sqlite3.Connection: ...
    def save_job(self, job: TranscriptionJob) -> None: ...
    def update_job(self, job: TranscriptionJob) -> None: ...
    def get_job(self, job_id: str) -> Optional[TranscriptionJob]: ...
    def list_jobs(self) -> list[TranscriptionJob]: ...
    def save_transcript(self, transcript: Transcript) -> None: ...
    def get_transcript_by_job_id(self, job_id: str) -> Optional[Transcript]: ...
```

**Rules:**
- `threading.RLock` on all write operations
- `segments_json` stores `list[dict]` serialized via `json.dumps`
- Dates stored as ISO format strings: `datetime.utcnow().isoformat()`
- `get_job` returns `None` if not found — never raises KeyError
- Create tables in `__init__` if they do not exist

---

### Module 2: `api/job_processor.py`

**Responsibility:** Accept a TranscriptionJob, run the full pipeline
(download → extract → transcribe) in a background thread, update job status,
and persist the result. Non-blocking from the API perspective.

**Interface:**
```python
class JobProcessor:
    def __init__(self, repository: TranscriptRepository,
                 download_dir: str): ...
    def submit(self, job: TranscriptionJob) -> None: ...
    def _process(self, job: TranscriptionJob) -> None: ...
```

**`_process` sequence:**
1. `repository.update_job(job)` — persist PENDING state
2. `YouTubeHandler.download(url, job)` — sets DOWNLOADING, populates metadata
3. `repository.update_job(job)` — persist DOWNLOADING state
4. `AudioExtractor.extract(video_path, job_dir, job)` — sets EXTRACTING
5. `repository.update_job(job)` — persist EXTRACTING state
6. `TranscriptionEngine.transcribe(audio_path, job, metadata)` — sets TRANSCRIBING
7. `job.mark_complete()`
8. `repository.update_job(job)` — persist COMPLETE
9. `repository.save_transcript(transcript)` — persist transcript
10. On any exception: `job.mark_failed(str(e))`, `repository.update_job(job)`

Run `_process` in `threading.Thread(target=self._process, args=(job,), daemon=True)`.

---

### Module 3: `api/main.py`

**Responsibility:** FastAPI application entry point. Configure CORS, mount routes,
initialize shared dependencies (repository, job processor) on startup.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.middleware.cors import configure_cors
from api.routes import jobs
from storage.repository import TranscriptRepository
from api.job_processor import JobProcessor
import os
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db_path = os.getenv("DB_PATH", "./nth_transcripts.db")
    download_dir = os.getenv("DOWNLOAD_DIR", "./downloads")
    app.state.repository = TranscriptRepository(db_path=db_path)
    app.state.processor = JobProcessor(
        repository=app.state.repository,
        download_dir=download_dir
    )
    yield
    # Shutdown — nothing to clean up

app = FastAPI(
    title="NTH Transcript Engine API",
    description="Video transcription via yt-dlp + faster-whisper",
    version="1.0.0",
    lifespan=lifespan
)

configure_cors(app)
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
```

---

### Module 4: `api/routes/jobs.py`

**Four endpoints:**

```
POST   /jobs                    — Submit a YouTube URL for transcription
GET    /jobs                    — List all jobs (status summary)
GET    /jobs/{job_id}           — Get job status
GET    /jobs/{job_id}/transcript — Get completed transcript
```

**POST /jobs behavior:**
1. Validate URL via `YouTubeHandler.validate_url()` — return 400 if invalid
2. Create `TranscriptionJob` with source_url and whisper_model from request
3. `repository.save_job(job)` — persist immediately
4. `processor.submit(job)` — fire background thread
5. Return 202 Accepted with `JobStatusResponse`

**GET /jobs/{job_id} behavior:**
- Return 404 if job_id not found
- Return `JobStatusResponse` with current status

**GET /jobs/{job_id}/transcript behavior:**
- Return 404 if job not found
- Return 409 if job status is not COMPLETE
- Return 200 with `TranscriptResponse`

**GET /jobs behavior:**
- Return list of `JobStatusResponse` for all jobs, newest first

---

### Module 5: `api/middleware/cors.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def configure_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],        # Tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

---

## Updated requirements.txt (Full — Sprint 1 + Sprint 2)

```
# NTH Transcript Engine — Sprint 1 + Sprint 2 Dependencies
yt-dlp>=2024.1.0
faster-whisper>=1.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
pytest-asyncio>=0.23.0
```

---

## Directory Structure After Sprint 2

```
NTH_TRANSCRIPT_ENGINE/
├── CLAUDE.md                               ← Frozen (Sprint 1)
├── CLAUDE_MASTER_SPRINT_1.md               ← Frozen (Sprint 1)
├── CLAUDE_MASTER_SPRINT_2.md               ← This file
├── models/
│   └── transcript.py                       ← FROZEN (Sprint 1)
├── ingestion/
│   ├── __init__.py                         ← FROZEN (Sprint 1)
│   └── youtube_handler.py                  ← FROZEN (Sprint 1)
├── transcription/
│   ├── __init__.py                         ← FROZEN (Sprint 1)
│   ├── audio_extractor.py                  ← FROZEN (Sprint 1)
│   └── engine.py                           ← FROZEN (Sprint 1)
├── storage/
│   ├── __init__.py                         ← NEW (Sprint 2)
│   └── repository.py                       ← NEW (Sprint 2)
├── api/
│   ├── __init__.py                         ← NEW (Sprint 2)
│   ├── main.py                             ← NEW (Sprint 2)
│   ├── job_processor.py                    ← NEW (Sprint 2)
│   ├── routes/
│   │   ├── __init__.py                     ← NEW (Sprint 2)
│   │   └── jobs.py                         ← NEW (Sprint 2)
│   └── middleware/
│       ├── __init__.py                     ← NEW (Sprint 2)
│       └── cors.py                         ← NEW (Sprint 2)
├── tests/
│   ├── test_sprint1_foundation.py          ← FROZEN (Sprint 1)
│   └── test_sprint2_api.py                 ← NEW (Sprint 2) — QA agent writes
├── requirements.txt                        ← MODIFIED (Sprint 2 appends 4 deps)
├── .env.example                            ← FROZEN (Sprint 1)
└── nth_transcripts.db                      ← Created at runtime
```

---

## Test Requirements — Sprint 2

**Minimum tests:** 14
**Test file:** `tests/test_sprint2_api.py`
**Written by:** QA Agent only

| # | Test Name | What It Validates |
|---|---|---|
| 1 | `test_repository_save_and_get_job` | save_job then get_job returns same job_id |
| 2 | `test_repository_update_job_status` | update_job persists status change |
| 3 | `test_repository_get_job_not_found` | get_job returns None for unknown ID |
| 4 | `test_repository_save_and_get_transcript` | save_transcript then get by job_id returns transcript |
| 5 | `test_repository_list_jobs` | list_jobs returns all saved jobs |
| 6 | `test_repository_transcript_segments_persist` | segments_json round-trips correctly |
| 7 | `test_api_submit_job_valid_url` | POST /jobs with valid YouTube URL returns 202 |
| 8 | `test_api_submit_job_invalid_url` | POST /jobs with invalid URL returns 400 |
| 9 | `test_api_get_job_status` | GET /jobs/{id} returns correct status |
| 10 | `test_api_get_job_not_found` | GET /jobs/{id} returns 404 for unknown ID |
| 11 | `test_api_get_transcript_not_complete` | GET /jobs/{id}/transcript returns 409 if not COMPLETE |
| 12 | `test_api_get_transcript_complete` | GET /jobs/{id}/transcript returns TranscriptResponse |
| 13 | `test_api_list_jobs` | GET /jobs returns list |
| 14 | `test_repository_thread_safety` | Concurrent writes do not corrupt job data |
| 15 | `test_sprint1_regression` | All Sprint 1 model imports still clean |

**Hard Gate Tests:**
- `test_repository_save_and_get_job` — persistence integrity
- `test_api_submit_job_valid_url` — API gateway
- `test_api_get_transcript_complete` — end-to-end data flow

---

## Definition of Done — Sprint 2

- [ ] Sprint 1 regression: `pytest tests/test_sprint1_foundation.py -v` — all 15 pass
- [ ] `storage/__init__.py` delivered
- [ ] `storage/repository.py` — TranscriptRepository importable, both tables created
- [ ] `api/__init__.py` delivered
- [ ] `api/main.py` — FastAPI app importable
- [ ] `api/job_processor.py` — JobProcessor importable
- [ ] `api/routes/__init__.py` delivered
- [ ] `api/routes/jobs.py` — 4 endpoints registered
- [ ] `api/middleware/__init__.py` delivered
- [ ] `api/middleware/cors.py` — configure_cors importable
- [ ] `requirements.txt` updated with 4 new dependencies
- [ ] `tests/test_sprint2_api.py` — minimum 14 tests
- [ ] All Sprint 2 tests pass: `pytest tests/test_sprint2_api.py -v`
- [ ] Hard gate tests all PASS
- [ ] Full suite passes: `pytest tests/ -v` (Sprint 1 + Sprint 2)
- [ ] `git diff --name-only` shows zero modifications to Sprint 1 frozen files
- [ ] `uvicorn api.main:app --reload` starts without error
- [ ] git commit: `sprint2: api layer complete`

---

## API Launch Command

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Manual verification after launch:**
```bash
# Submit a job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "whisper_model": "base"}'

# Check status
curl http://localhost:8000/jobs/{job_id}

# Get transcript (once COMPLETE)
curl http://localhost:8000/jobs/{job_id}/transcript
```

---

## PM Agent Launch Prompt

```
You are the PM Agent for Sprint 2 of the NTH Transcript Engine.

Read CLAUDE_MASTER_SPRINT_2.md completely before taking any action.

Sprint 1 is complete and frozen. Your FIRST action is to run the Sprint 1
regression check before any Sprint 2 code is written:

  pytest tests/test_sprint1_foundation.py -v

All 15 Sprint 1 tests must pass. If any fail — halt and report to user.
Do not write a single Sprint 2 file until regression passes.

Execute in this sequence:
1. Run Sprint 1 regression (gate — must pass before proceeding)
2. Direct Backend Agent Phase 2a: storage/repository.py + storage/__init__.py
3. Direct Backend Agent Phase 2b: api/job_processor.py
4. Direct Backend Agent Phase 2c: api/middleware/, api/routes/, api/main.py
5. Direct Backend Agent to update requirements.txt (append 4 deps, pip install)
6. Import verification for all new modules
7. QA Gate 1: Hard gate tests (repository + API submission + transcript retrieval)
8. QA Gate 2: Full suite — pytest tests/ -v (Sprint 1 + Sprint 2)
9. Verify frozen assets untouched: git diff --name-only HEAD
10. DoD report — explicit PASS/FAIL every item
11. git commit: sprint2: api layer complete

Critical constraint: models/transcript.py is frozen. api/routes/jobs.py uses
Pydantic schemas (SubmitJobRequest, JobStatusResponse, etc.) for the API layer
only. These schemas NEVER redefine or replace the dataclasses in models/transcript.py.
```
