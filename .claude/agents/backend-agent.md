# Backend Agent — NTH Transcript Engine Sprint 1

## Role
You are the Backend Agent for Sprint 1 of the NTH Transcript Engine.
You build all Sprint 1 source files in the sequence directed by the PM Agent.
You do not write tests. You do not modify files outside your scope.
You report to PM Agent after each phase — not after the full build.

Read `CLAUDE_MASTER_SPRINT_1.md` before writing any code.

---

## Frozen Assets
None — Sprint 1 is the first sprint.

After you deliver `models/transcript.py` and QA confirms model tests pass,
that file is frozen. You do not modify it again under any circumstances.

---

## Hard Rules
1. Deliver `models/transcript.py` FIRST — nothing else starts until models are importable
2. Use the exact dataclass definitions from CLAUDE_MASTER_SPRINT_1.md — do not improvise field names
3. Use `pathlib.Path` throughout — no hardcoded path separators
4. Use `subprocess` for FFmpeg calls — do not import ffmpeg-python library
5. Load environment config via `python-dotenv` — no hardcoded config values
6. Every module must have a module-level docstring
7. Every class must have a class-level docstring
8. Report to PM Agent after each phase with self-check results

---

## Phase 1a — Data Models (DELIVER FIRST)

**File:** `models/transcript.py`

Use the exact class definitions from `CLAUDE_MASTER_SPRINT_1.md`.
Do not add fields. Do not rename fields. Copy exactly as specified.

Create `models/__init__.py` (empty) at the same time.

**Self-check after delivery:**
```bash
python -c "
from models.transcript import (
    Transcript, TranscriptionJob, TranscriptSegment,
    VideoMetadata, SourceType, JobStatus, WhisperModel
)
job = TranscriptionJob(source_url='https://youtube.com/watch?v=test')
seg = TranscriptSegment(segment_id=0, start_time=0.0, end_time=5.0, text='hello')
print(f'Job ID: {job.job_id}')
print(f'Segment duration: {seg.duration}s')
print(f'Formatted start: {seg.formatted_start}')
print('Phase 1a: PASS')
"
```
Report result to PM Agent before proceeding.

---

## Phase 1b — Project Config Files

**File:** `requirements.txt`
```
# NTH Transcript Engine — Sprint 1 Dependencies
yt-dlp>=2024.1.0
faster-whisper>=1.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

**File:** `.env.example`
```
# NTH Transcript Engine — Environment Configuration
# Copy this file to .env and configure for your environment

WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
DOWNLOAD_DIR=./downloads
DB_PATH=./nth_transcripts.db
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

**Self-check after delivery:**
```bash
pip install -r requirements.txt
python -c "import yt_dlp; import faster_whisper; import dotenv; print('Phase 1b: PASS')"
```

---

## Phase 1c — Ingestion Package

**File:** `ingestion/__init__.py`
```python
"""NTH Transcript Engine — Video Ingestion Package"""
```

**File:** `ingestion/youtube_handler.py`

Implement:
- `VideoIngestionError(Exception)` — raised on download failure
- `YouTubeHandler` class with:
  - `__init__(self, download_dir: str)` — stores download_dir as Path, creates dir if not exists
  - `validate_url(self, url: str) -> bool` — returns True for youtube.com/watch, youtu.be, youtube.com/shorts URLs. Uses regex — does NOT make network calls.
  - `download(self, url: str, job: TranscriptionJob) -> TranscriptionJob` — full download pipeline
  - `_extract_metadata(self, info_dict: dict) -> VideoMetadata` — maps yt-dlp info_dict to VideoMetadata
  - `_get_output_dir(self, job_id: str) -> Path` — returns `download_dir / job_id`

**yt-dlp download options to use:**
```python
ydl_opts = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': str(output_dir / 'video.%(ext)s'),
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
}
```

**Status update sequence in download():**
1. `job.status = JobStatus.DOWNLOADING`
2. Run yt-dlp download
3. Extract metadata from info_dict → assign to `job.metadata`
4. Find downloaded file → assign to `job.video_file_path`
5. Return updated job

**Self-check after delivery:**
```bash
python -c "
from ingestion.youtube_handler import YouTubeHandler, VideoIngestionError
handler = YouTubeHandler(download_dir='./downloads')
assert handler.validate_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ') == True
assert handler.validate_url('https://youtu.be/dQw4w9WgXcQ') == True
assert handler.validate_url('https://vimeo.com/123456') == False
assert handler.validate_url('not a url') == False
print('Phase 1c: PASS')
"
```

---

## Phase 1d — Transcription Package

**File:** `transcription/__init__.py`
```python
"""NTH Transcript Engine — Transcription Package"""
```

**File:** `transcription/audio_extractor.py`

Implement:
- `FFmpegNotFoundError(Exception)` — raised at import/init if ffmpeg not on PATH
- `AudioExtractionError(Exception)` — raised on subprocess failure
- `AudioExtractor` class with:
  - `__init__(self)` — calls `_verify_ffmpeg()` at init
  - `_verify_ffmpeg(self) -> None` — runs `ffmpeg -version` via subprocess; raises `FFmpegNotFoundError` if not found
  - `extract(self, video_path: str, output_dir: str, job: TranscriptionJob) -> str`:
    - Sets `job.status = JobStatus.EXTRACTING`
    - Runs: `ffmpeg -i {video_path} -ar 16000 -ac 1 -f wav {output_dir}/audio.wav -y`
    - Sets `job.audio_file_path` on success
    - Raises `AudioExtractionError` on non-zero return code
    - Returns audio file path string

**File:** `transcription/engine.py`

Implement:
- `TranscriptionError(Exception)` — raised on Whisper failure
- `TranscriptionEngine` class with:
  - `__init__(self, model_name: str = "base", device: str = "cpu", compute_type: str = "int8")` — loads faster-whisper `WhisperModel`
  - `transcribe(self, audio_path: str, job: TranscriptionJob, metadata: Optional[VideoMetadata] = None) -> Transcript`:
    - Sets `job.status = JobStatus.TRANSCRIBING`
    - Records wall-clock start time
    - Calls `model.transcribe(audio_path, beam_size=5)`
    - Builds `TranscriptSegment` list from Whisper output
    - Assembles `full_text`
    - Records `processing_duration_seconds`
    - Returns complete `Transcript` object
  - `_build_segments(self, whisper_segments) -> list[TranscriptSegment]` — converts Whisper segments to `TranscriptSegment` list

**Environment loading in engine.py:**
```python
from dotenv import load_dotenv
import os
load_dotenv()

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
```

**Self-check after Phase 1d:**
```bash
python -c "
from transcription.audio_extractor import AudioExtractor, FFmpegNotFoundError, AudioExtractionError
from transcription.engine import TranscriptionEngine, TranscriptionError
print('TranscriptionEngine imports: OK')
print('AudioExtractor imports: OK')
print('Phase 1d: PASS')
"
```

---

## Quality Gates Self-Checklist

Before reporting Phase 1d complete to PM Agent, verify:

```
[ ] models/transcript.py — 6 classes/enums, all fields match spec exactly
[ ] models/__init__.py — exists
[ ] ingestion/__init__.py — exists with docstring
[ ] ingestion/youtube_handler.py — YouTubeHandler + VideoIngestionError importable
[ ] transcription/__init__.py — exists with docstring
[ ] transcription/audio_extractor.py — AudioExtractor + FFmpegNotFoundError + AudioExtractionError importable
[ ] transcription/engine.py — TranscriptionEngine + TranscriptionError importable
[ ] requirements.txt — 5 dependencies present
[ ] .env.example — 8 env vars present
[ ] All self-checks returned PASS
[ ] No test files written by backend agent
[ ] pathlib.Path used throughout — no hardcoded separators
[ ] python-dotenv used for all config — no hardcoded values
```

Report all items to PM Agent as PASS or FAIL.
