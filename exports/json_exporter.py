"""
NTH Transcript Engine — Structured JSON Exporter
Sprint 4 | Owner: Backend Agent

Pure function — no I/O, no API, no repository access.
"""

import json

from models.transcript import Transcript


def export_json(transcript: Transcript) -> str:
    """Render a Transcript as a structured JSON document."""
    payload = {
        "transcript_id": transcript.transcript_id,
        "job_id": transcript.job_id,
        "full_text": transcript.full_text,
        "language_detected": transcript.language_detected,
        "whisper_model_used": transcript.whisper_model_used,
        "segment_count": transcript.segment_count,
        "word_count": transcript.word_count,
        "processing_duration_seconds": transcript.processing_duration_seconds,
        "created_at": transcript.created_at.isoformat(),
        "segments": [
            {
                "segment_id": s.segment_id,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "formatted_start": s.formatted_start,
                "formatted_end": s.formatted_end,
                "text": s.text,
                "confidence": s.confidence,
            }
            for s in transcript.segments
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
