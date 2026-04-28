"""
NTH Transcript Engine — Vimeo Ingestion Handler
Sprint 5 | Owner: Backend Agent

Uses yt-dlp's native Vimeo extractor.
"""

import re
from pathlib import Path

from models.transcript import (
    JobStatus,
    SourceType,
    TranscriptionJob,
    VideoMetadata,
)


class VimeoIngestionError(Exception):
    """Raised when Vimeo ingestion fails."""


_VIMEO_URL_RE = re.compile(
    r"^(https?://)?(www\.|player\.)?vimeo\.com/(video/\d+|\d+|[\w\-]+/[\w\-]+)"
    r"(/[\w\-]+)?(\?[^\s]*)?$",
    re.IGNORECASE,
)


class VimeoHandler:
    """Downloads Vimeo videos and extracts metadata via yt-dlp."""

    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def validate_url(self, url: str) -> bool:
        if not isinstance(url, str) or not url.strip():
            return False
        return bool(_VIMEO_URL_RE.match(url.strip()))

    def download(self, url: str, job: TranscriptionJob) -> TranscriptionJob:
        if not self.validate_url(url):
            job.mark_failed(f"Invalid Vimeo URL: {url}")
            raise VimeoIngestionError(f"Invalid Vimeo URL: {url}")

        job.status = JobStatus.DOWNLOADING
        job.source_url = url
        job.source_type = SourceType.VIMEO

        job_dir = self.download_dir / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            import yt_dlp
        except ImportError as e:
            job.mark_failed(f"yt-dlp not installed: {e}")
            raise VimeoIngestionError(f"yt-dlp not installed: {e}") from e

        output_template = str(job_dir / "video.%(ext)s")
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise VimeoIngestionError("yt-dlp returned no info for Vimeo URL")
                ext = info.get("ext", "mp4")
                video_path = job_dir / f"video.{ext}"
                if not video_path.exists():
                    candidates = list(job_dir.glob("video.*"))
                    if not candidates:
                        raise VimeoIngestionError(
                            f"Downloaded video file not found in {job_dir}"
                        )
                    video_path = candidates[0]
                job.video_file_path = str(video_path)
                job.metadata = VideoMetadata(
                    title=info.get("title", "Unknown"),
                    duration_seconds=float(info.get("duration", 0) or 0),
                    source_url=info.get("webpage_url", url),
                    source_type=SourceType.VIMEO,
                    uploader=info.get("uploader"),
                    upload_date=info.get("upload_date"),
                    description=info.get("description"),
                    thumbnail_url=info.get("thumbnail"),
                    view_count=info.get("view_count"),
                    language=info.get("language"),
                )
                return job
        except VimeoIngestionError:
            raise
        except Exception as e:
            job.mark_failed(f"Vimeo download failed: {e}")
            raise VimeoIngestionError(f"Vimeo download failed: {e}") from e
