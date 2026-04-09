"""
NTH Transcript Engine — SQLite Repository
Sprint 2 | Owner: Backend Agent
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.transcript import (
    JobStatus,
    SourceType,
    Transcript,
    TranscriptionJob,
    TranscriptSegment,
    VideoMetadata,
    WhisperModel,
)


_CREATE_JOBS = """
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
"""

_CREATE_TRANSCRIPTS = """
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
"""


class TranscriptRepository:
    """SQLite-backed persistence for TranscriptionJob and Transcript objects."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._get_connection() as conn:
            conn.execute(_CREATE_JOBS)
            conn.execute(_CREATE_TRANSCRIPTS)
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------- jobs ----------------------------------

    def save_job(self, job: TranscriptionJob) -> None:
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO jobs (
                        job_id, source_url, source_type, whisper_model, status,
                        created_at, completed_at, error_message,
                        audio_file_path, video_file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job.job_id,
                        job.source_url,
                        job.source_type.value,
                        job.whisper_model.value,
                        job.status.value,
                        job.created_at.isoformat(),
                        job.completed_at.isoformat() if job.completed_at else None,
                        job.error_message,
                        job.audio_file_path,
                        job.video_file_path,
                    ),
                )
                conn.commit()

    def update_job(self, job: TranscriptionJob) -> None:
        # INSERT OR REPLACE handles both create and update
        self.save_job(job)

    def get_job(self, job_id: str) -> Optional[TranscriptionJob]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def list_jobs(self) -> list[TranscriptionJob]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def _row_to_job(self, row: sqlite3.Row) -> TranscriptionJob:
        job = TranscriptionJob(
            job_id=row["job_id"],
            source_url=row["source_url"],
            source_type=SourceType(row["source_type"]),
            whisper_model=WhisperModel(row["whisper_model"]),
            status=JobStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=(
                datetime.fromisoformat(row["completed_at"])
                if row["completed_at"]
                else None
            ),
            error_message=row["error_message"],
            audio_file_path=row["audio_file_path"],
            video_file_path=row["video_file_path"],
        )
        return job

    # ---------------------------- transcripts ------------------------------

    def save_transcript(self, transcript: Transcript) -> None:
        segments_payload = [
            {
                "segment_id": s.segment_id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "text": s.text,
                "confidence": s.confidence,
            }
            for s in transcript.segments
        ]
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO transcripts (
                        transcript_id, job_id, full_text, language_detected,
                        whisper_model_used, segment_count, word_count,
                        processing_duration_seconds, created_at, segments_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        transcript.transcript_id,
                        transcript.job_id,
                        transcript.full_text,
                        transcript.language_detected,
                        transcript.whisper_model_used,
                        transcript.segment_count,
                        transcript.word_count,
                        transcript.processing_duration_seconds,
                        transcript.created_at.isoformat(),
                        json.dumps(segments_payload),
                    ),
                )
                conn.commit()

    def get_transcript_by_job_id(self, job_id: str) -> Optional[Transcript]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM transcripts WHERE job_id = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        segs_data = json.loads(row["segments_json"])
        segments = [
            TranscriptSegment(
                segment_id=s["segment_id"],
                start_time=s["start_time"],
                end_time=s["end_time"],
                text=s["text"],
                confidence=s.get("confidence"),
            )
            for s in segs_data
        ]
        return Transcript(
            transcript_id=row["transcript_id"],
            job_id=row["job_id"],
            metadata=None,  # not persisted at this layer in Sprint 2
            segments=segments,
            full_text=row["full_text"],
            language_detected=row["language_detected"],
            whisper_model_used=row["whisper_model_used"],
            created_at=datetime.fromisoformat(row["created_at"]),
            processing_duration_seconds=row["processing_duration_seconds"],
        )
