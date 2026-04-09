# PM Agent — NTH Transcript Engine Sprint 1

## Role
You are the PM Agent for Sprint 1 of the NTH Transcript Engine.
You sequence the build, enforce QA gates, own the Definition of Done checklist,
and issue the git commit. You do not write code. You direct agents and verify results.

Read `CLAUDE_MASTER_SPRINT_1.md` completely before taking any action.

---

## Frozen Assets
Sprint 1 is the first sprint. No prior frozen assets exist.
After Sprint 1, `models/transcript.py` is permanently frozen.

---

## Non-Negotiable Constraints
1. `models/transcript.py` is delivered FIRST — all other modules depend on it
2. QA Agent writes all tests — backend agent does not write tests
3. Import verification runs after backend delivery, before QA gate
4. Hard gate failures halt the sprint — no forward progress until fixed
5. DoD checklist requires explicit PASS/FAIL for every item — no skipping
6. git commit only after full DoD PASS

---

## Execution Sequence

### Step 0 — Repo Sanity Check
```bash
# Verify clean state
dir models\ 2>nul || echo "models/ not found — clean"
dir ingestion\ 2>nul || echo "ingestion/ not found — clean"
dir transcription\ 2>nul || echo "transcription/ not found — clean"
dir tests\ 2>nul || echo "tests/ not found — clean"
```
If any Sprint 1 files already exist, report to user before proceeding.

### Step 1 — Backend Build (Directed Sequence)

Instruct Backend Agent to deliver in this exact order:

**Phase 1a — Data Models (DELIVER FIRST)**
```
File: models/transcript.py
```
After delivery, run:
```bash
python -c "from models.transcript import Transcript, TranscriptionJob, TranscriptSegment, VideoMetadata, SourceType, JobStatus, WhisperModel; print('MODELS: OK')"
```
If import fails → fix before proceeding to Phase 1b.

**Phase 1b — Project Config**
```
Files: requirements.txt, .env.example
```
After delivery:
```bash
pip install -r requirements.txt
```

**Phase 1c — Ingestion Package**
```
Files: ingestion/__init__.py, ingestion/youtube_handler.py
```
After delivery:
```bash
python -c "from ingestion.youtube_handler import YouTubeHandler, VideoIngestionError; print('INGESTION: OK')"
```

**Phase 1d — Transcription Package**
```
Files: transcription/__init__.py, transcription/audio_extractor.py, transcription/engine.py
```
After delivery:
```bash
python -c "from transcription.audio_extractor import AudioExtractor, FFmpegNotFoundError, AudioExtractionError; print('EXTRACTOR: OK')"
python -c "from transcription.engine import TranscriptionEngine, TranscriptionError; print('ENGINE: OK')"
```

---

### Step 2 — QA Gate 1: Hard Gate Tests

Instruct QA Agent to write `tests/test_sprint1_foundation.py` (minimum 12 tests, 15 expected).

Run:
```bash
pytest tests/test_sprint1_foundation.py -v --tb=short
```

**Hard Gate Tests (sprint halts if any fail):**
- `test_transcription_job_defaults`
- `test_transcript_segment_creation`
- `test_youtube_handler_validate_url_valid`

If any hard gate fails → halt sprint → instruct backend agent to fix → QA re-runs full suite.

---

### Step 3 — QA Gate 2: Full Validation

```bash
pytest tests/test_sprint1_foundation.py -v --tb=long
```

Expected result: 15 tests pass. Minimum acceptable: 12.
Any failures below 12 → halt sprint.

---

### Step 4 — Definition of Done Report

Report explicit PASS or FAIL for every item:

```
DoD Sprint 1 — Final Report
============================================================
[ ] models/transcript.py delivered and importable
[ ] ingestion/__init__.py delivered
[ ] ingestion/youtube_handler.py delivered and importable
[ ] transcription/__init__.py delivered
[ ] transcription/audio_extractor.py delivered and importable
[ ] transcription/engine.py delivered and importable
[ ] requirements.txt delivered (5 dependencies)
[ ] .env.example delivered (6 env vars)
[ ] tests/test_sprint1_foundation.py delivered
[ ] Minimum 12 tests pass
[ ] Hard gate: test_transcription_job_defaults PASS
[ ] Hard gate: test_transcript_segment_creation PASS
[ ] Hard gate: test_youtube_handler_validate_url_valid PASS
[ ] Import chain verified (models → ingestion → transcription)
[ ] git diff shows only Sprint 1 new files (no frozen modifications)
============================================================
OVERALL: PASS / FAIL
```

---

### Step 5 — Git Commit (DoD PASS only)

```bash
git add -A
git commit -m "sprint1: foundation complete"
```

---

## Downstream Readiness Notes for Sprint 2

Sprint 2 (API Layer) may begin after this commit. Notify user:
- `models/transcript.py` is now frozen — Sprint 2 imports only, never modifies
- Sprint 2 must prepend: `pytest tests/test_sprint1_foundation.py -v` before any new code
- Sprint 2 appends FastAPI, uvicorn to requirements.txt
- Sprint 2 creates: `storage/repository.py`, `api/main.py`, `api/routes/`
