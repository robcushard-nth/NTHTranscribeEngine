"""
NTH Transcript Engine — Direct URL Ingestion Handler
Sprint 5 | Owner: Backend Agent
"""

from pathlib import Path
from urllib.parse import urlparse

import httpx

from models.transcript import (
    JobStatus,
    SourceType,
    TranscriptionJob,
    VideoMetadata,
)


class DirectURLIngestionError(Exception):
    """Raised when direct URL ingestion fails."""


_VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv",
                     ".mp3", ".wav", ".m4a")
_YOUTUBE_HOSTS = ("youtube.com", "youtu.be")
_VIMEO_HOSTS = ("vimeo.com",)
_HTTP_SCHEMES = ("http", "https")
_CHUNK_BYTES = 16 * 1024 * 1024  # 16 MB


class DirectURLHandler:
    """Streams an http(s) media resource to disk via httpx."""

    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def validate_url(self, url: str) -> bool:
        if not isinstance(url, str) or not url.strip():
            return False
        try:
            parsed = urlparse(url.strip())
        except ValueError:
            return False
        if parsed.scheme.lower() not in _HTTP_SCHEMES:
            return False
        host = (parsed.netloc or "").lower()
        if any(host == h or host.endswith("." + h) for h in _YOUTUBE_HOSTS):
            return False
        if any(host == h or host.endswith("." + h) for h in _VIMEO_HOSTS):
            return False
        path = (parsed.path or "").lower()
        return path.endswith(_VIDEO_EXTENSIONS)

    def download(self, url: str, job: TranscriptionJob) -> TranscriptionJob:
        if not self.validate_url(url):
            job.mark_failed(f"Invalid direct video URL: {url}")
            raise DirectURLIngestionError(f"Invalid direct video URL: {url}")

        job.status = JobStatus.DOWNLOADING
        job.source_url = url
        job.source_type = SourceType.DIRECT_URL

        job_dir = self.download_dir / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(urlparse(url).path).suffix.lower() or ".mp4"
        target = job_dir / f"video{ext}"

        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as resp:
                resp.raise_for_status()
                with open(target, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=_CHUNK_BYTES):
                        if chunk:
                            f.write(chunk)
        except httpx.HTTPError as e:
            job.mark_failed(f"Direct URL download failed: {e}")
            raise DirectURLIngestionError(f"Direct URL download failed: {e}") from e
        except OSError as e:
            job.mark_failed(f"Disk write failed: {e}")
            raise DirectURLIngestionError(f"Disk write failed: {e}") from e

        if not target.exists() or target.stat().st_size == 0:
            job.mark_failed("Direct URL download produced no file")
            raise DirectURLIngestionError("Direct URL download produced no file")

        job.video_file_path = str(target)
        job.metadata = VideoMetadata(
            title=Path(urlparse(url).path).stem or "remote_video",
            duration_seconds=0.0,
            source_url=url,
            source_type=SourceType.DIRECT_URL,
        )
        return job
