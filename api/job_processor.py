"""
NTH Transcript Engine — Background Job Processor
Sprint 2 | Owner: Backend Agent
"""

import threading
from pathlib import Path

from ingestion.local_file_handler import LocalFileHandler
from ingestion.url_handler import DirectURLHandler
from ingestion.vimeo_handler import VimeoHandler
from ingestion.youtube_handler import YouTubeHandler
from models.transcript import SourceType, TranscriptionJob
from storage.repository import TranscriptRepository
from transcription.audio_extractor import AudioExtractor
from transcription.engine import TranscriptionEngine


class JobProcessor:
    """Runs the full transcription pipeline in a daemon background thread."""

    def __init__(self, repository: TranscriptRepository, download_dir: str):
        self.repository = repository
        self.download_dir = download_dir
        Path(download_dir).mkdir(parents=True, exist_ok=True)
        self.youtube = YouTubeHandler(download_dir=download_dir)
        self.vimeo = VimeoHandler(download_dir=download_dir)
        self.direct_url = DirectURLHandler(download_dir=download_dir)
        self.local_file = LocalFileHandler(download_dir=download_dir)

    def submit(self, job: TranscriptionJob) -> None:
        thread = threading.Thread(
            target=self._process,
            args=(job,),
            daemon=True,
            name=f"job-{job.job_id[:8]}",
        )
        thread.start()

    def _process(self, job: TranscriptionJob) -> None:
        try:
            self.repository.update_job(job)

            if job.source_type is SourceType.YOUTUBE:
                self.youtube.download(job.source_url, job)
            elif job.source_type is SourceType.VIMEO:
                self.vimeo.download(job.source_url, job)
            elif job.source_type is SourceType.DIRECT_URL:
                self.direct_url.download(job.source_url, job)
            elif job.source_type is SourceType.LOCAL_FILE:
                self.local_file.ingest(job.source_url, job)
            else:
                raise ValueError(f"Unsupported source_type: {job.source_type}")
            self.repository.update_job(job)

            job_dir = str(Path(self.download_dir) / job.job_id)
            extractor = AudioExtractor()
            audio_path = extractor.extract(job.video_file_path, job_dir, job)
            self.repository.update_job(job)

            engine = TranscriptionEngine(model_name=job.whisper_model.value)
            transcript = engine.transcribe(audio_path, job, metadata=job.metadata)

            job.mark_complete()
            self.repository.update_job(job)
            self.repository.save_transcript(transcript)
        except Exception as e:
            job.mark_failed(str(e))
            try:
                self.repository.update_job(job)
            except Exception:
                pass
