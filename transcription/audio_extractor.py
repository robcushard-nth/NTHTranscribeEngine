"""
NTH Transcript Engine — FFmpeg Audio Extractor
Sprint 1 | Owner: Backend Agent
"""

import shutil
import subprocess
from pathlib import Path

from models.transcript import JobStatus, TranscriptionJob


class AudioExtractionError(Exception):
    """Raised when FFmpeg audio extraction fails."""


class FFmpegNotFoundError(Exception):
    """Raised when the FFmpeg binary cannot be located on PATH."""


class AudioExtractor:
    """Extracts 16kHz mono WAV audio from a video file using FFmpeg."""

    def __init__(self):
        self._verify_ffmpeg()

    def _verify_ffmpeg(self) -> None:
        if shutil.which("ffmpeg") is None:
            raise FFmpegNotFoundError(
                "FFmpeg not found on PATH. Install FFmpeg and ensure 'ffmpeg' "
                "is available from the command line."
            )

    def extract(
        self,
        video_path: str,
        output_dir: str,
        job: TranscriptionJob,
    ) -> str:
        job.status = JobStatus.EXTRACTING

        video = Path(video_path)
        if not video.exists():
            msg = f"Video file does not exist: {video_path}"
            job.mark_failed(msg)
            raise AudioExtractionError(msg)

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        audio_path = out_dir / "audio.wav"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "wav",
            str(audio_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as e:
            job.mark_failed(f"FFmpeg invocation failed: {e}")
            raise FFmpegNotFoundError(str(e)) from e

        if result.returncode != 0:
            err = result.stderr.strip() or "unknown ffmpeg error"
            job.mark_failed(f"FFmpeg failed: {err}")
            raise AudioExtractionError(f"FFmpeg failed: {err}")

        if not audio_path.exists():
            job.mark_failed("FFmpeg did not produce audio output")
            raise AudioExtractionError("FFmpeg did not produce audio output")

        job.audio_file_path = str(audio_path)
        return str(audio_path)
