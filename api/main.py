"""
NTH Transcript Engine — FastAPI Application Entry Point
Sprint 2 | Owner: Backend Agent
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from api.job_processor import JobProcessor
from api.middleware.cors import configure_cors
from api.routes import jobs
from storage.repository import TranscriptRepository

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.getenv("DB_PATH", "./nth_transcripts.db")
    download_dir = os.getenv("DOWNLOAD_DIR", "./downloads")
    app.state.repository = TranscriptRepository(db_path=db_path)
    app.state.processor = JobProcessor(
        repository=app.state.repository,
        download_dir=download_dir,
    )
    yield


app = FastAPI(
    title="NTH Transcript Engine API",
    description="Video transcription via yt-dlp + faster-whisper",
    version="1.0.0",
    lifespan=lifespan,
)

configure_cors(app)
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
