"""
NTH Transcript Engine — Transcript Export Endpoint
Sprint 4 | Owner: Backend Agent

Single endpoint that returns a completed transcript in TXT/SRT/JSON/DOCX form
as a file download. Loads transcripts via the existing TranscriptRepository.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from exports.docx_exporter import export_docx
from exports.json_exporter import export_json
from exports.srt_exporter import export_srt
from exports.txt_exporter import export_txt
from models.transcript import JobStatus


router = APIRouter()


_FORMAT_TABLE = {
    "txt": (
        "text/plain; charset=utf-8",
        "txt",
    ),
    "srt": (
        "application/x-subrip; charset=utf-8",
        "srt",
    ),
    "json": (
        "application/json; charset=utf-8",
        "json",
    ),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx",
    ),
}


@router.get("/{job_id}/transcript/export")
def export_transcript(
    job_id: str,
    request: Request,
    format: str = Query(..., description="One of: txt, srt, json, docx"),
) -> Response:
    fmt = format.lower().strip()
    if fmt not in _FORMAT_TABLE:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown format '{format}'. Expected one of: txt, srt, json, docx",
        )

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
            status_code=404, detail=f"No transcript stored for job {job_id}"
        )

    media_type, ext = _FORMAT_TABLE[fmt]

    if fmt == "txt":
        body: bytes = export_txt(transcript).encode("utf-8")
    elif fmt == "srt":
        body = export_srt(transcript).encode("utf-8")
    elif fmt == "json":
        body = export_json(transcript).encode("utf-8")
    else:  # docx
        body = export_docx(transcript)

    short = job_id[:8]
    filename = f"transcript_{short}.{ext}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=body, media_type=media_type, headers=headers)
