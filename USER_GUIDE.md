# NTH Transcript Engine — User Guide

This guide walks you through using the NTH Transcript Engine from a user's perspective: starting the app, submitting a video, watching it process, reading the transcript, and exporting results.

For installation, configuration, architecture, and the REST API reference, see [README.md](README.md).

---

## Table of Contents

1. [What this tool does](#what-this-tool-does)
2. [Before you start](#before-you-start)
3. [Starting the app](#starting-the-app)
4. [Dashboard tour](#dashboard-tour)
5. [Submitting a transcription job](#submitting-a-transcription-job)
6. [Tracking job progress](#tracking-job-progress)
7. [Reading a transcript](#reading-a-transcript)
8. [Exporting transcripts](#exporting-transcripts)
9. [Using the history panel](#using-the-history-panel)
10. [Choosing the right Whisper model](#choosing-the-right-whisper-model)
11. [Tips and best practices](#tips-and-best-practices)
12. [Common problems](#common-problems)
13. [Using the app without the UI](#using-the-app-without-the-ui)

---

## What this tool does

Give it **any one of these**:

- A **YouTube URL** (`youtube.com/watch?v=...`, `youtu.be/...`, `/shorts/...`, `/embed/...`)
- A **Vimeo URL** (`vimeo.com/123456`, `player.vimeo.com/video/...`)
- A **direct video or audio URL** (`https://example.com/clip.mp4`, also `.mov`, `.mkv`, `.avi`, `.webm`, `.flv`, `.mp3`, `.wav`, `.m4a`)
- A **local file path** on this machine (any of the same media extensions — e.g. `C:\Users\You\Videos\meeting.mp4` or `D:\audio\recording.mp3`)

It:

1. **Fetches the source** — downloads it (YouTube/Vimeo/direct URL) or copies it into the working directory (local file).
2. Extracts the audio with FFmpeg.
3. Transcribes the audio locally using a Whisper model (no cloud API, no data leaves the machine).
4. Saves the transcript with timestamps to a local database.
5. Lets you browse, copy, and export the transcript as TXT, SRT, JSON, or DOCX.

Typical uses:
- Transcribing internal meeting recordings (Zoom, Teams, Webex) from your local Downloads folder — audio never leaves the host.
- Building searchable archives of interviews, webinars, or lectures from public sources.
- Generating `.srt` subtitle files for re-uploading video.
- Producing DOCX transcripts for review, quoting, or compliance.
- Getting structured JSON segments for downstream text analysis or LLM input.

---

## Before you start

You need:

- The app installed and dependencies in place. See the [README Installation section](README.md#installation).
- **FFmpeg** available on your system PATH. Confirm with `ffmpeg -version`.
- **A reachable internet connection** — only required for YouTube, Vimeo, and direct URL sources. **Local file ingestion runs fully offline.**
- **A valid source** you have the right to transcribe — a YouTube/Vimeo URL, a direct media URL, or a local file path.

---

## Starting the app

Open **two** terminals in the project directory.

**Terminal 1 — start the API:**

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Wait until you see `Application startup complete.`

**Terminal 2 — start the UI:**

```bash
python -m ui.app
```

Run it as a module from the project root — not `python ui/app.py`, which fails with `ModuleNotFoundError: No module named 'ui'` because the dashboard uses absolute imports (`from ui.colors import ...`).

Then open your browser to:

```
http://localhost:8080
```

You should see the **NTH Transcript Engine** dashboard.

> Keep both terminals open while you use the app. Closing either one stops the service.

---

## Dashboard tour

The dashboard is a single page with a header and three columns.

```
┌──────────────────────────────────────────────────────────────────────┐
│  NTH Transcript Engine                               NTH AI Dynamics │
├───────────────────┬─────────────────────┬────────────────────────────┤
│                   │                     │                            │
│  Submit Job       │  History            │  Transcript Viewer         │
│  (left column)    │  (center column)    │  (right column, 50% wide)  │
│                   │                     │                            │
│  • URL input      │  • Newest jobs top  │  • Video title / duration  │
│  • Model selector │  • Status dots      │  • Segmented transcript    │
│  • Transcribe btn │  • Click to load    │  • Full text + Copy        │
│  • Status badge   │  • Refresh button   │  • Export TXT/SRT/JSON/DOCX│
└───────────────────┴─────────────────────┴────────────────────────────┘
```

- **Submit Job (left)** — where you start a new transcription.
- **History (center)** — list of every job the engine has processed, newest first.
- **Transcript Viewer (right)** — shows the currently selected transcript with timestamps and export buttons.

---

## Submitting a transcription job

1. In the **Submit Job** panel, paste a **video source** into the input field. The label reads "Video Source (URL or local file path)" — you can give it any of:

   | Source | Example |
   |---|---|
   | YouTube | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
   | Vimeo | `https://vimeo.com/123456` |
   | Direct video URL | `https://example.com/clip.mp4` |
   | Local video file | `C:\Users\You\Videos\meeting.mp4` |
   | Local audio file | `C:\Users\You\Downloads\interview.mp3` |

   The API auto-detects which kind of source it is — you don't have to tell it.

2. Pick a **Whisper model** from the dropdown. If you're unsure, start with `base`. See [Choosing the right Whisper model](#choosing-the-right-whisper-model).
3. Click **Transcribe**.
4. The status badge turns amber and shows `pending`. A `job_id` appears — that's the unique identifier for this run.

You do **not** need to wait on this panel. You can submit the job and go do something else. When it finishes, the viewer loads the transcript automatically and the history refreshes.

> **Windows tip — "Copy as path" inserts an invisible character.** When you right-click a file in File Explorer and choose *Copy as path*, Windows prepends a U+202A bidi mark to the clipboard. The handler strips it automatically (and also strips surrounding quotes), so you can paste straight from Explorer with no manual cleanup. If you ever see "Unrecognized source" on a path you know exists, double-check the path doesn't have a trailing space and that the file extension is one of the supported ones above.

---

## Tracking job progress

The engine moves through these states:

| Status | What's happening |
|---|---|
| `pending` | Job accepted. Waiting to start. |
| `downloading` | The source is being fetched. YouTube/Vimeo: yt-dlp. Direct URL: httpx streamed download. Local file: in-process copy into `downloads/{job_id}/`. |
| `extracting` | FFmpeg is stripping audio to a 16 kHz mono WAV. |
| `transcribing` | faster-whisper is running the selected model over the audio. |
| `complete` | Transcript is saved and ready to view/export. |
| `failed` | Something went wrong. Hover the badge or check the API terminal for the error. |

The submission panel polls the API and updates the badge color:

- **Amber** — in progress (any state before `complete`).
- **Green** — complete.
- **Red** — failed.

**How long does it take?** Depends on model, hardware, and audio length. Rough rule of thumb on a modern CPU:

- `tiny` / `base`: ~0.1–0.3× real-time (a 10-min video in 1–3 min).
- `small`: ~0.3–0.6× real-time.
- `medium`: ~1–2× real-time.
- `large-v3`: 3×+ real-time on CPU; much faster on GPU.

The first run with a given model also pays a one-time download of the model weights.

---

## Reading a transcript

Once the job status is `complete`, the **Transcript Viewer** panel shows:

- **Video metadata** — title, duration, and (when available) uploader.
- **Segmented transcript** — one line per Whisper segment:
  ```
  [00:00:03] Welcome to the show.
  [00:00:06] Today we're talking about...
  ```
  Each segment has a start timestamp in `HH:MM:SS` format.
- **Full text area** — the same transcript as one continuous block, suitable for selecting/copying.
- **Copy button** — puts the full text on your clipboard.
- **Export buttons** — TXT, SRT, JSON, DOCX (see next section).

Scroll the segment view to move through the video chronologically. The timestamps align with playback positions on the original video, so you can use them to jump back into the source clip.

---

## Exporting transcripts

Click one of the four export buttons on the viewer panel. Your browser will download a file.

| Format | Extension | Best for |
|---|---|---|
| **TXT** | `.txt` | Readable plain text with `[HH:MM:SS]` timestamps. Good for notes, email, search. |
| **SRT** | `.srt` | Subtitle file for re-uploading to YouTube, Vimeo, or adding to a video editor. Millisecond-precise. |
| **JSON** | `.json` | Structured data — segments, timestamps, metadata, language. Good for downstream tooling or LLM input. |
| **DOCX** | `.docx` | Word document with bold timestamps. Good for hand-off to stakeholders who want to review in Word. |

All exports are generated on demand from the database, so you can re-export the same job any time, in any format, without re-running transcription.

> **Tip:** for a full episode upload to YouTube, the `.srt` file can be attached as closed captions. For a searchable knowledge base, push the `.json` into your indexer.

---

## Using the history panel

The **History** panel lists every job the engine has processed, newest first.

- Each entry shows a **status dot** (colored like the submission badge), a snippet of the source URL, and the created timestamp.
- **Click any entry** to load its transcript into the viewer. You don't need to keep the submission panel around — the history is the source of truth.
- **Refresh** syncs with the database (useful if multiple people are using the same API).

The history is backed by the SQLite database at `nth_transcripts.db`, so it persists across restarts.

---

## Choosing the right Whisper model

Whisper model size trades speed for quality. Use this decision tree:

- **Clean speech, single speaker, English, quick draft** → `base`.
- **Noisier audio, multiple speakers, or non-English** → `small` or `medium`.
- **Hard audio, accents, or accuracy is critical** → `large-v3`. Expect slow CPU performance.
- **You have a GPU** → `medium` or `large-v3` with `WHISPER_DEVICE=cuda` and `WHISPER_COMPUTE_TYPE=float16`.

You can pick the model per-job in the UI. Each job records which model it used, so you can re-run a URL at a higher quality later if the first pass was rough.

---

## Tips and best practices

- **Short segments transcribe faster than long ones** — not because of per-minute cost (transcription is roughly linear), but because you can iterate and spot-check sooner. For a new source, try a 10-minute clip before committing to a 2-hour keynote.
- **Clean audio matters more than model size.** A noisy `large-v3` run can still be worse than a clean `base` run.
- **Leave the API running.** The job processor lives in the API process. If you restart the API mid-job, in-flight work is lost — you'll need to resubmit.
- **Disk hygiene.** The `downloads/` folder accumulates raw video and intermediate WAVs. Clean it periodically if disk space is tight.
- **Re-exports are free.** Pick whichever format you need at the moment; the transcript is regenerated from the DB, not re-transcribed.
- **Model weights are cached** by faster-whisper in the user's home directory. You only pay the download once per model, not once per job.

---

## Common problems

**"Transcribe" does nothing.**
The API isn't running, or the UI can't reach it. Check Terminal 1 for `Application startup complete.` and confirm the UI's `API_BASE_URL` (default `http://localhost:8000`) matches.

**Status jumps to `failed` immediately.**
Depends on the source kind:
- *YouTube / Vimeo:* usually a yt-dlp extractor break — try the URL in a browser to confirm it plays, then `pip install -U yt-dlp` and retry.
- *Direct URL:* the server returned non-2xx or the URL doesn't end in a media extension the validator accepts. Use the actual file URL, not an embed page.
- *Local file:* either the path doesn't exist, the extension isn't supported, or a `Permission denied` reading the source. Check the API terminal for the exact reason.

**Submission rejected with 400 "Unrecognized source".**
The input didn't match any of the four source types. Common causes:
- Trailing space or stray quote on a pasted URL.
- Local file with an extension outside `.mp4 / .mov / .mkv / .avi / .webm / .flv / .mp3 / .wav / .m4a`.
- A redirect-style or query-string URL where the path component doesn't end in a media extension — point to the real file, not a player page.

**Status stuck on `downloading` for a long time.**
Large videos or slow networks. Watch the API terminal — yt-dlp / httpx log progress there. For local files this stage should take seconds; if it's stuck, the source file is unusually large or on a slow / network drive.

**Status stuck on `transcribing` for a long time.**
Normal on CPU with larger models. Check the API terminal for Whisper progress. If it's truly hung, cancel (Ctrl-C the API) and retry with a smaller model.

**Export button downloads an empty file.**
The job probably isn't `complete` yet, or completed with zero segments. Check the viewer — if segments are empty, the source audio may be silent or undetectable; try a different model.

**UI shows an error toast on load.**
The UI couldn't fetch history from the API. Confirm the API is up and reload the page.

**Where is my data?**
- Transcripts and jobs: `nth_transcripts.db` in the project root.
- Downloaded video + extracted audio: `downloads/` in the project root.
- Whisper model weights: cached in your user profile by faster-whisper (outside this repo).

---

## Using the app without the UI

The UI is a convenience — everything it does is exposed on the REST API. If you prefer scripting:

```bash
# Submit — YouTube
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","whisper_model":"base"}'

# Submit — Vimeo
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"url":"https://vimeo.com/123456","whisper_model":"base"}'

# Submit — direct media URL
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/clip.mp4","whisper_model":"base"}'

# Submit — local file (backslashes JSON-escaped)
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"url":"C:\\Users\\You\\Videos\\meeting.mp4","whisper_model":"base"}'

# Poll
curl http://localhost:8000/jobs/<job_id>

# Get transcript when complete
curl http://localhost:8000/jobs/<job_id>/transcript

# Export as SRT (saves with server-suggested filename)
curl -OJ "http://localhost:8000/jobs/<job_id>/transcript/export?format=srt"
```

Swagger-style interactive docs are at [http://localhost:8000/docs](http://localhost:8000/docs) while the API is running — they let you try every endpoint from the browser without writing code.

---

See [README.md](README.md) for architecture, configuration, and developer setup.
