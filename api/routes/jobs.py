"""
NTH Transcript Engine — Jobs API Routes
Sprint 2 | Owner: Backend Agent

Pydantic schemas defined here are API-layer DTOs only — they do NOT replace
the dataclasses in models/transcript.py (which remain frozen).
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from ingestion.youtube_handler import YouTubeHandler
from models.transcript import (
    JobStatus,
    SourceType,
    TranscriptionJob,
    WhisperModel,
)


# ----------------------------- Pydantic schemas ------------------------------

class SubmitJobRequest(BaseModel):
    url: str
    whisper_model: Optional[str] = "base"


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
    language_detected: Optional[str] = None
    whisper_model_used: str
    segment_count: int
    word_count: int
    processing_duration_seconds: Optional[float] = None
    segments: list[SegmentResponse]
    created_at: str


# ---------------------------------- helpers ----------------------------------

def _job_to_response(job: TranscriptionJob) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        source_url=job.source_url,
        whisper_model=job.whisper_model.value,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error_message=job.error_message,
    )


# ---------------------------------- router -----------------------------------

router = APIRouter()
_url_validator = YouTubeHandler.__new__(YouTubeHandler)  # validate_url is stateless


@router.post("", response_model=JobStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_job(payload: SubmitJobRequest, request: Request) -> JobStatusResponse:
    if not _url_validator.validate_url(payload.url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YouTube URL: {payload.url}",
        )

    try:
        whisper_model = WhisperModel(payload.whisper_model or "base")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown whisper_model: {payload.whisper_model}",
        )

    job = TranscriptionJob(
        source_url=payload.url,
        source_type=SourceType.YOUTUBE,
        whisper_model=whisper_model,
        status=JobStatus.PENDING,
    )

    repo = request.app.state.repository
    processor = request.app.state.processor

    repo.save_job(job)
    processor.submit(job)
    return _job_to_response(job)


@router.get("", response_model=list[JobStatusResponse])
def list_jobs(request: Request) -> list[JobStatusResponse]:
    repo = request.app.state.repository
    jobs = repo.list_jobs()
    return [_job_to_response(j) for j in jobs]


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, request: Request) -> JobStatusResponse:
    repo = request.app.state.repository
    job = repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return _job_to_response(job)


@router.get("/{job_id}/transcript", response_model=TranscriptResponse)
def get_transcript(job_id: str, request: Request) -> TranscriptResponse:
    repo = request.app.state.repository
    job = repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if job.status is not JobStatus.COMPLETE:
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} not complete (status={job.status.value})",
        )
    transcript = repo.get_transcript_by_job_id(job_id)
    if transcript is None:
        raise HTTPException(
            status_code=404,
            detail=f"No transcript stored for job {job_id}",
        )

    seg_responses = [
        SegmentResponse(
            segment_id=s.segment_id,
            start_time=s.start_time,
            end_time=s.end_time,
            formatted_start=s.formatted_start,
            formatted_end=s.formatted_end,
            text=s.text,
        )
        for s in transcript.segments
    ]

    return TranscriptResponse(
        transcript_id=transcript.transcript_id,
        job_id=transcript.job_id,
        full_text=transcript.full_text,
        language_detected=transcript.language_detected,
        whisper_model_used=transcript.whisper_model_used,
        segment_count=transcript.segment_count,
        word_count=transcript.word_count,
        processing_duration_seconds=transcript.processing_duration_seconds,
        segments=seg_responses,
        created_at=transcript.created_at.isoformat(),
    )
