# Backend Agent — NTH Transcript Engine Sprint 2

## Role
You are the Backend Agent for Sprint 2 of the NTH Transcript Engine.
You build the storage repository, job processor, and FastAPI application.
You do not write tests. You do not modify frozen files.
Report to PM Agent after each phase.

Read `CLAUDE_MASTER_SPRINT_2.md` before writing any code.

---

## Frozen Assets — Do Not Touch
- `models/transcript.py`
- `ingestion/youtube_handler.py`
- `transcription/audio_extractor.py`
- `transcription/engine.py`
- `tests/test_sprint1_foundation.py`

Permitted: append to `requirements.txt` only.

---

## Hard Rules
1. Import `TranscriptionJob`, `Transcript`, `TranscriptSegment` from `models.transcript` — never redefine
2. Pydantic schemas (SubmitJobRequest etc.) live in `api/routes/jobs.py` — they are API-layer only
3. `threading.RLock` on all repository write operations
4. `pathlib.Path` throughout — no hardcoded separators
5. `python-dotenv` for all config — no hardcoded values
6. No test code written by backend agent

---

## Phase 2a — Storage Repository

### `storage/__init__.py`
```python
"""NTH Transcript Engine — Storage Package"""
```

### `storage/repository.py`

Full implementation requirements:

```python
"""
NTH Transcript Engine — Transcript Repository
Sprint 2 | Owner: Backend Agent
Thread-safe SQLite persistence for TranscriptionJob and Transcript.
"""

import sqlite3
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional
from models.transcript import (
    TranscriptionJob, Transcript, TranscriptSegment,
    VideoMetadata, SourceType, JobStatus, WhisperModel
)


class TranscriptRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self) -> None:
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
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
                    )
                """)
                conn.execute("""
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
                    )
                """)
                conn.commit()
    # ... implement all methods per spec
```

**Implement each method as specified in CLAUDE_MASTER_SPRINT_2.md.**

Key implementation notes:
- `save_job` / `update_job`: serialize `SourceType.value`, `JobStatus.value`, `WhisperModel.value`
- `get_job`: deserialize enums via `SourceType(row['source_type'])` etc.
- `save_transcript`: serialize segments via `json.dumps([{'segment_id': s.segment_id, 'start_time': s.start_time, 'end_time': s.end_time, 'text': s.text, 'confidence': s.confidence} for s in transcript.segments])`
- `get_transcript_by_job_id`: deserialize segments from JSON
- `list_jobs`: ORDER BY created_at DESC

**Self-check:**
```bash
python -c "
from storage.repository import TranscriptRepository
from models.transcript import TranscriptionJob, JobStatus
repo = TranscriptRepository(db_path=':memory:')
job = TranscriptionJob(source_url='https://youtube.com/watch?v=test')
repo.save_job(job)
retrieved = repo.get_job(job.job_id)
assert retrieved.job_id == job.job_id
assert retrieved.status == JobStatus.PENDING
job.mark_complete()
repo.update_job(job)
updated = repo.get_job(job.job_id)
assert updated.status == JobStatus.COMPLETE
print('Phase 2a: PASS')
"
```

---

## Phase 2b — Job Processor

### `api/job_processor.py`

```python
"""
NTH Transcript Engine — Background Job Processor
Sprint 2 | Owner: Backend Agent
Runs transcription pipeline in a daemon thread.
"""

import threading
import logging
from pathlib import Path
from models.transcript import TranscriptionJob, JobStatus
from ingestion.youtube_handler import YouTubeHandler, VideoIngestionError
from transcription.audio_extractor import AudioExtractor, AudioExtractionError
from transcription.engine import TranscriptionEngine, TranscriptionError
from storage.repository import TranscriptRepository

logger = logging.getLogger(__name__)


class JobProcessor:
    def __init__(self, repository: TranscriptRepository, download_dir: str):
        self.repository = repository
        self.download_dir = download_dir
        self._youtube_handler = YouTubeHandler(download_dir=download_dir)
        self._audio_extractor = AudioExtractor()

    def submit(self, job: TranscriptionJob) -> None:
        """Submit job for background processing. Returns immediately."""
        thread = threading.Thread(
            target=self._process,
            args=(job,),
            daemon=True,
            name=f"job-{job.job_id[:8]}"
        )
        thread.start()

    def _process(self, job: TranscriptionJob) -> None:
        """Full pipeline: download → extract → transcribe → persist."""
        try:
            # 1. Download
            self._youtube_handler.download(job.source_url, job)
            self.repository.update_job(job)

            # 2. Extract audio
            job_dir = str(Path(self.download_dir) / job.job_id)
            self._audio_extractor.extract(job.video_file_path, job_dir, job)
            self.repository.update_job(job)

            # 3. Transcribe
            import os
            from dotenv import load_dotenv
            load_dotenv()
            engine = TranscriptionEngine(
                model_name=job.whisper_model.value,
                device=os.getenv("WHISPER_DEVICE", "cpu"),
                compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8")
            )
            transcript = engine.transcribe(job.audio_file_path, job, job.metadata)

            # 4. Persist result
            job.mark_complete()
            self.repository.update_job(job)
            self.repository.save_transcript(transcript)
            logger.info(f"Job {job.job_id[:8]} complete — {transcript.word_count} words")

        except (VideoIngestionError, AudioExtractionError, TranscriptionError) as e:
            logger.error(f"Job {job.job_id[:8]} failed: {e}")
            job.mark_failed(str(e))
            self.repository.update_job(job)
        except Exception as e:
            logger.error(f"Job {job.job_id[:8]} unexpected error: {e}")
            job.mark_failed(f"Unexpected error: {str(e)}")
            self.repository.update_job(job)
```

**Self-check:**
```bash
python -c "
from api.job_processor import JobProcessor
from storage.repository import TranscriptRepository
repo = TranscriptRepository(':memory:')
proc = JobProcessor(repository=repo, download_dir='./downloads')
print('Phase 2b: PASS')
"
```

---

## Phase 2c — API Layer

### `api/__init__.py`
```python
"""NTH Transcript Engine — API Package"""
```

### `api/middleware/__init__.py`
```python
"""NTH Transcript Engine — API Middleware"""
```

### `api/middleware/cors.py`
Implement exactly as specified in CLAUDE_MASTER_SPRINT_2.md.

### `api/routes/__init__.py`
```python
"""NTH Transcript Engine — API Routes"""
```

### `api/routes/jobs.py`

Implement all four endpoints exactly per spec. Key details:

**POST /jobs:**
```python
@router.post("/", status_code=202, response_model=JobStatusResponse)
async def submit_job(request: SubmitJobRequest, req: Request):
    handler = YouTubeHandler(download_dir=os.getenv("DOWNLOAD_DIR", "./downloads"))
    if not handler.validate_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported YouTube URL")
    
    job = TranscriptionJob(
        source_url=request.url,
        whisper_model=WhisperModel(request.whisper_model)
    )
    req.app.state.repository.save_job(job)
    req.app.state.processor.submit(job)
    return _job_to_response(job)
```

**GET /jobs/{job_id}/transcript:**
```python
@router.get("/{job_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(job_id: str, req: Request):
    job = req.app.state.repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.COMPLETE:
        raise HTTPException(status_code=409, detail=f"Job not complete. Status: {job.status.value}")
    transcript = req.app.state.repository.get_transcript_by_job_id(job_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return _transcript_to_response(transcript)
```

Add private helper functions `_job_to_response` and `_transcript_to_response`
to convert domain objects to Pydantic response models.

### `api/main.py`
Implement exactly as specified in CLAUDE_MASTER_SPRINT_2.md.

### Update `requirements.txt`
Append (do not overwrite):
```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
pytest-asyncio>=0.23.0
```

Then:
```bash
pip install -r requirements.txt
```

**Self-check after Phase 2c:**
```bash
python -c "from api.main import app; print(f'Routes: {[r.path for r in app.routes]}'); print('Phase 2c: PASS')"
```

---

## Quality Gates Self-Checklist

```
[ ] storage/__init__.py — exists
[ ] storage/repository.py — TranscriptRepository, both tables created on init
[ ] api/__init__.py — exists
[ ] api/job_processor.py — JobProcessor, submit() and _process() implemented
[ ] api/middleware/__init__.py — exists
[ ] api/middleware/cors.py — configure_cors implemented
[ ] api/routes/__init__.py — exists
[ ] api/routes/jobs.py — 4 endpoints + Pydantic schemas + helper functions
[ ] api/main.py — FastAPI app with lifespan, CORS, router mounted
[ ] requirements.txt — 4 dependencies appended and installed
[ ] All self-checks returned PASS
[ ] Zero test code written by backend agent
[ ] models/transcript.py not modified
[ ] threading.RLock used in repository
[ ] pathlib.Path used throughout
[ ] python-dotenv used for all config
```
