"""
NTH Transcript Engine — SubRip (SRT) Exporter
Sprint 4 | Owner: Backend Agent

Pure function — no I/O, no API, no repository access.
"""

from models.transcript import Transcript


def _format_srt_timestamp(seconds: float) -> str:
    """Convert float seconds to SRT timestamp 'HH:MM:SS,mmm'."""
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    hours, rem_ms = divmod(total_ms, 3_600_000)
    minutes, rem_ms = divmod(rem_ms, 60_000)
    secs, ms = divmod(rem_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def export_srt(transcript: Transcript) -> str:
    """Render a Transcript as a SubRip subtitle string.

    Format per segment:
        {index}
        HH:MM:SS,mmm --> HH:MM:SS,mmm
        text
        <blank line>
    Index starts at 1.
    """
    blocks: list[str] = []
    for idx, seg in enumerate(transcript.segments, start=1):
        start = _format_srt_timestamp(seg.start_time)
        end = _format_srt_timestamp(seg.end_time)
        text = seg.text.strip()
        blocks.append(f"{idx}\n{start} --> {end}\n{text}\n")
    return "\n".join(blocks)
