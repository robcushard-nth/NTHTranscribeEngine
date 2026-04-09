"""
NTH Transcript Engine — YouTube Ingestion Handler
Sprint 1 | Owner: Backend Agent
"""

import re
from pathlib import Path
from typing import Optional

from models.transcript import (
    JobStatus,
    SourceType,
    TranscriptionJob,
    VideoMetadata,
)


class VideoIngestionError(Exception):
    """Raised when YouTube ingestion fails."""


_YOUTUBE_URL_RE = re.compile(
    r"^(https?://)?(www\.)?"
    r"(youtube\.com/(watch\?v=|embed/|v/|shorts/)[\w\-]+"
    r"|youtu\.be/[\w\-]+)"
    r"([&?][^\s]*)?$",
    re.IGNORECASE,
)


class YouTubeHandler:
    """Downloads YouTube videos and extracts metadata via yt-dlp."""

    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def validate_url(self, url: str) -> bool:
        if not isinstance(url, str) or not url.strip():
            return False
        return bool(_YOUTUBE_URL_RE.match(url.strip()))

    def download(self, url: str, job: TranscriptionJob) -> TranscriptionJob:
        if not self.validate_url(url):
            job.mark_failed(f"Invalid YouTube URL: {url}")
            raise VideoIngestionError(f"Invalid YouTube URL: {url}")

        job.status = JobStatus.DOWNLOADING
        job.source_url = url
        job.source_type = SourceType.YOUTUBE

        job_dir = self.download_dir / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            import yt_dlp  # imported lazily so test environment doesn't require it
        except ImportError as e:
            job.mark_failed(f"yt-dlp not installed: {e}")
            raise VideoIngestionError(f"yt-dlp not installed: {e}") from e

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
                    raise VideoIngestionError("yt-dlp returned no info")
                metadata = self._extract_metadata(info)
                # Locate the actual file written
                ext = info.get("ext", "mp4")
                video_path = job_dir / f"video.{ext}"
                if not video_path.exists():
                    # fall back to any video.* in the directory
                    candidates = list(job_dir.glob("video.*"))
                    if not candidates:
                        raise VideoIngestionError(
                            f"Downloaded video file not found in {job_dir}"
                        )
                    video_path = candidates[0]
                job.video_file_path = str(video_path)
                job.metadata = metadata
                return job
        except VideoIngestionError:
            raise
        except Exception as e:
            job.mark_failed(f"YouTube download failed: {e}")
            raise VideoIngestionError(f"YouTube download failed: {e}") from e

    def _extract_metadata(self, info_dict: dict) -> VideoMetadata:
        return VideoMetadata(
            title=info_dict.get("title", "Unknown"),
            duration_seconds=float(info_dict.get("duration", 0) or 0),
            source_url=info_dict.get("webpage_url", ""),
            source_type=SourceType.YOUTUBE,
            uploader=info_dict.get("uploader"),
            upload_date=info_dict.get("upload_date"),
            description=info_dict.get("description"),
            thumbnail_url=info_dict.get("thumbnail"),
            view_count=info_dict.get("view_count"),
            language=info_dict.get("language"),
        )
