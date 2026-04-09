"""
NTH Transcript Engine — Plain Text Exporter
Sprint 4 | Owner: Backend Agent

Pure function — no I/O, no API, no repository access.
"""

from models.transcript import Transcript


def export_txt(transcript: Transcript) -> str:
    """Render a Transcript as timestamped plain text.

    Format:
        # Transcript {transcript_id}
        # Words: {word_count}
        [HH:MM:SS] segment text
        [HH:MM:SS] segment text
        ...
    """
    lines: list[str] = []
    lines.append(f"# Transcript {transcript.transcript_id}")
    lines.append(f"# Words: {transcript.word_count}")
    for seg in transcript.segments:
        text = seg.text.strip()
        lines.append(f"[{seg.formatted_start}] {text}")
    return "\n".join(lines) + "\n"
