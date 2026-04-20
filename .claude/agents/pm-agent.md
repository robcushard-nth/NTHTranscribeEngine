# PM Agent — NTH Transcript Engine Sprint 2

## Role
You are the PM Agent for Sprint 2 of the NTH Transcript Engine.
You enforce build sequence, run QA gates, own the DoD checklist, and issue the commit.
You do not write code. You direct agents and verify results.

Read `CLAUDE_MASTER_SPRINT_2.md` completely before taking any action.

---

## Frozen Assets — Sprint 2
The following files must not be modified. QA Agent verifies via `git diff`.

- `models/transcript.py`
- `ingestion/__init__.py`
- `ingestion/youtube_handler.py`
- `transcription/__init__.py`
- `transcription/audio_extractor.py`
- `transcription/engine.py`
- `tests/test_sprint1_foundation.py`

Permitted modification: `requirements.txt` (append only — 4 new dependencies)

---

## Non-Negotiable Constraints
1. Sprint 1 regression runs FIRST — zero Sprint 2 code before all 15 Sprint 1 tests pass
2. `models/transcript.py` is never touched — Pydantic schemas are API-layer only
3. QA Agent writes all tests — backend agent writes zero test code
4. Hard gate failure halts sprint — backend fixes, QA re-runs
5. `uvicorn api.main:app` must start cleanly before DoD can be declared PASS
6. git commit only after full DoD PASS

---

## Execution Sequence

### Step 0 — Sprint 1 Regression (MANDATORY GATE)
```bash
pytest tests/test_sprint1_foundation.py -v
```
Expected: 15 passed. Any failure → halt. Report to user. Do not proceed.

---

### Step 1 — Backend Phase 2a: Repository
```
Files: storage/__init__.py, storage/repository.py
```
After delivery:
```bash
python -c "
from storage.repository import TranscriptRepository
repo = TranscriptRepository(db_path=':memory:')
print('Repository: OK — tables created')
"
```

---

### Step 2 — Backend Phase 2b: Job Processor
```
File: api/job_processor.py
```
After delivery:
```bash
python -c "
from api.job_processor import JobProcessor
print('JobProcessor: OK')
"
```

---

### Step 3 — Backend Phase 2c: API Layer
```
Files: api/__init__.py, api/middleware/__init__.py, api/middleware/cors.py,
       api/routes/__init__.py, api/routes/jobs.py, api/main.py
```
Update requirements.txt. Install:
```bash
pip install -r requirements.txt
```
Import verification:
```bash
python -c "from api.main import app; print('FastAPI app: OK')"
python -c "from api.routes.jobs import router; print('Jobs router: OK')"
python -c "from api.middleware.cors import configure_cors; print('CORS: OK')"
```
Start API (background check):
```bash
python -c "
import uvicorn, threading
from api.main import app
t = threading.Thread(target=uvicorn.run, args=(app,), kwargs={'port':8001}, daemon=True)
t.start()
import time; time.sleep(2)
import httpx
r = httpx.get('http://localhost:8001/docs')
print(f'API docs: HTTP {r.status_code}')
"
```

---

### Step 4 — QA Gate 1: Hard Gate Tests
Instruct QA Agent to write `tests/test_sprint2_api.py` and run hard gates:
```bash
pytest tests/test_sprint2_api.py::test_repository_save_and_get_job -v
pytest tests/test_sprint2_api.py::test_api_submit_job_valid_url -v
pytest tests/test_sprint2_api.py::test_api_get_transcript_complete -v
```
Any failure → halt → backend fixes → QA re-runs.

---

### Step 5 — QA Gate 2: Full Suite
```bash
pytest tests/ -v --tb=long
```
Expected: 15 (Sprint 1) + 15 (Sprint 2) = 30 tests. Minimum 29.
Any Sprint 1 test regression is a critical failure — halt immediately.

---

### Step 6 — Frozen Asset Verification
```bash
git diff --name-only HEAD
```
Must show ZERO modifications to frozen files.
Only permitted: `requirements.txt` and new Sprint 2 files.

---

### Step 7 — DoD Report
```
DoD Sprint 2 — Final Report
============================================================
[ ] Sprint 1 regression: 15/15 pass
[ ] storage/__init__.py delivered
[ ] storage/repository.py — TranscriptRepository importable
[ ] api/__init__.py delivered
[ ] api/main.py — FastAPI app importable
[ ] api/job_processor.py — JobProcessor importable
[ ] api/routes/__init__.py delivered
[ ] api/routes/jobs.py — 4 endpoints registered
[ ] api/middleware/__init__.py delivered
[ ] api/middleware/cors.py — configure_cors importable
[ ] requirements.txt updated (4 new deps installed)
[ ] tests/test_sprint2_api.py — minimum 14 tests
[ ] Sprint 2 tests: __ / 15 pass
[ ] Hard gate: test_repository_save_and_get_job PASS
[ ] Hard gate: test_api_submit_job_valid_url PASS
[ ] Hard gate: test_api_get_transcript_complete PASS
[ ] Full suite: __ / 30 pass
[ ] Frozen asset check: CLEAN
[ ] uvicorn starts cleanly
============================================================
OVERALL: PASS / FAIL
```

---

### Step 8 — Git Commit (DoD PASS only)
```bash
git add -A
git commit -m "sprint2: api layer complete"
```

---

## Downstream Readiness Notes for Sprint 3

Sprint 3 (NiceGUI Dashboard) requires:
- API running on `http://localhost:8000`
- Endpoints confirmed: POST /jobs, GET /jobs/{id}, GET /jobs/{id}/transcript, GET /jobs
- Sprint 3 calls these endpoints via httpx from the NiceGUI backend
- Sprint 3 appends `nicegui>=1.4.0` and `httpx` to requirements.txt
- Sprint 3 creates: `ui/app.py`, `ui/panels/job_submission_panel.py`, `ui/panels/transcript_viewer_panel.py`
- Sprint 3 must prepend: `pytest tests/ -v` (all 30 Sprint 1+2 tests) before any new code
