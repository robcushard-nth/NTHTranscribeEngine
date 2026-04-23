# NTH Transcript Engine — Project Portfolio

**Author:** William "Rob" Cushard — Fractional COO / AI Operations Strategist
**Organization:** NTH AI Dynamics / NTH Simple Solution Corp
**Contact:** rob.cushard@nthsimplesolution.com | 470-426-4144
**Repository:** [github.com/robcushard-nth/NTHTranscribeEngine](https://github.com/robcushard-nth/NTHTranscribeEngine)
**Engagement Model:** NTH internal product — sovereign AI reference build
**Status:** Active Development — Sprints 1–4 Complete (Sprint 5 roadmapped: multi-source ingestion)
**Build Window:** 2026-04-09 → 2026-04-23 (14 calendar days)
**Last Updated:** 2026-04-23

---

## One-Line Summary

A local-only, sovereign transcription platform that converts video (YouTube today, arbitrary sources next) into timestamped, exportable transcripts using OpenAI Whisper running on the operator's own machine — zero third-party API calls, four-agent sprint delivery, 58 passing tests across four sprints in fourteen days.

---

## Business Problem Solved

Operations teams, fractional executives, and regulated-industry clients need searchable transcripts of meetings, interviews, podcasts, and training videos. Commercial transcription services (Otter, Rev, AssemblyAI, OpenAI Whisper API) require shipping audio to a third party — a non-starter for ITAR, CMMC, HIPAA, NDA-bound, or attorney-client-privileged content. Self-hosted options exist but ship as research code, not as an operator-ready tool.

This engine closes that gap: paste a URL, pick a model size, click Transcribe, download as TXT / SRT / JSON / DOCX. Audio never leaves the host machine. An operator with no Python experience can run it.

---

## Size Metrics

Every number below pulled from the repo at commit `9724672` via `git`, `find`, and `wc -l` — not estimates.

| Metric | Value | Source |
|---|---|---|
| Python source LOC | 1,760 | `find . -name "*.py" -not -path "*/tests/*"` + `wc -l` |
| Python test LOC | 903 | `find tests -name "*.py" | wc -l` |
| Total Python LOC | 2,663 | combined |
| Markdown docs LOC | 4,682 | includes sprint master specs + README + guides |
| Python source files | 29 | non-test, non-venv |
| Python test files | 5 | including `tests/__init__.py` |
| Total tracked files | 52 | excludes venv, downloads, pycache, .git |
| Test-to-source ratio | 34% LOC, 17% files | QA-Agent-owned coverage |
| Tests written | 58 | 16 + 15 + 10 + 17 across four sprints |
| Git commits | 6 | `git rev-list --count HEAD` |
| Git tags | 0 | sprints tracked via commit messages, not tags |
| Calendar build days | 14 | first commit `2026-04-09`, last `2026-04-23` |

---

## Technology Stack

Pulled directly from [requirements.txt](requirements.txt):

| Layer | Technology | Version pin | Purpose |
|---|---|---|---|
| Language | Python | 3.11+ | Runtime |
| Video download | yt-dlp | ≥2024.1.0 | YouTube + platform ingestion |
| Audio extraction | FFmpeg 6.x | external binary | Video → 16 kHz mono WAV |
| Transcription | faster-whisper | ≥1.0.0 | Local Whisper (CPU int8 / CUDA float16) |
| REST API | FastAPI | ≥0.110.0 | `/jobs`, `/jobs/{id}`, `/jobs/{id}/transcript`, `/jobs/{id}/transcript/export` |
| API server | uvicorn[standard] | ≥0.29.0 | ASGI |
| UI framework | NiceGUI | ≥1.4.0 | Python-native web dashboard |
| HTTP client | httpx | ≥0.27.0 | Async API calls from UI |
| Storage | SQLite 3 | stdlib | `jobs` + `transcripts` tables |
| DOCX export | python-docx | ≥1.1.0 | Word file generation |
| Config | python-dotenv | ≥1.0.0 | `.env` loader |
| Tests | pytest / pytest-mock / pytest-asyncio | ≥8.0.0 / ≥3.12.0 / ≥0.23.0 | Unit + async + mock |

No Docker, no Kubernetes, no cloud dependencies. The stack is intentionally minimal and sovereign.

---

## Agent Architecture — Four-Agent Sprint Pattern™

The project runs on NTH's four-agent sprint delivery model. Each sprint drops four agent specs into `.claude/agents/` and a master doc at the repo root. Roles are non-overlapping and enforced via frozen-file verification:

| Agent | File | Primary Responsibility |
|---|---|---|
| **PM Agent** | [.claude/agents/pm-agent.md](.claude/agents/pm-agent.md) | Reads master doc, sequences phases, runs QA gates, owns the Definition of Done, issues the git commit. Writes zero code. |
| **Backend Agent** | [.claude/agents/backend-agent.md](.claude/agents/backend-agent.md) | Builds models, handlers, engine, repository, API layer in sequence. Writes zero tests. Cannot modify frozen files. |
| **Frontend Agent** | [.claude/agents/frontend-agent.md](.claude/agents/frontend-agent.md) | Builds NiceGUI panels after QA gates clear. Imports only from `models/` — never from `ingestion/`, `transcription/`, `storage/`, or `exports/`. All API calls via httpx. |
| **QA Agent** | [.claude/agents/qa-agent.md](.claude/agents/qa-agent.md) | Writes every test. Runs hard-gate tests (sprint-halting) and full-suite gates. Verifies frozen-asset integrity via `git diff`. Reports DoD to PM Agent. |

**Enforced separation of duties.** Backend agents never see test code. QA agents never touch source. Frontend agents cannot reach past the API. This is not cosmetic — the PM Agent halts sprints on frozen-file violations.

---

## Sprint History

Four sprints delivered in fourteen days. Every sprint shipped with a Definition of Done and a passing full-suite regression before commit.

| Sprint | Commit | Deliverable | Tests | DoD |
|---|---|---|---|---|
| 1 — Foundation | `6d89772` | `models/transcript.py` (frozen forever), YouTube handler (yt-dlp), FFmpeg audio extractor, faster-whisper engine | 16 | PASS |
| 2 — API Layer | `e8f1d09` | Thread-safe SQLite repository (`threading.RLock`), background `JobProcessor` daemon, FastAPI app with 4 endpoints, CORS | 15 | PASS |
| 3 — NiceGUI Dashboard | `f5cc138` | Three-column dashboard, submission panel with live status polling, transcript viewer, NTH dark-theme color system | 10 | PASS |
| 4 — Export Engine + History | `9ac7926` | TXT/SRT/JSON/DOCX pure-function exporters, export API endpoint, history panel with click-to-load | 17 | PASS |

**Frozen Asset Rule:** Prior-sprint files are immutable unless explicitly allowlisted in the current sprint's master doc. Sprint 4 modified exactly four files from earlier sprints — each on an explicit allowlist with a specific one-line permitted change. The QA Agent verified via `git diff --name-only HEAD` before commit.

**Sprint reshuffle on record:** The original Sprint 4 (multi-source ingestion — local file, direct URL, Vimeo) was deferred; the original Sprint 5 (export engine) was pulled forward and bundled with the history panel that had slipped out of Sprint 3 manual verification. This decision is documented in [.claude/agents/CLAUDE_MASTER_SPRINT_4.md](.claude/agents/CLAUDE_MASTER_SPRINT_4.md).

---

## Data Pipeline

`YouTube URL → yt-dlp (video.mp4) → FFmpeg (16 kHz mono WAV) → faster-whisper (segments + full_text) → SQLite (jobs + transcripts) → FastAPI → NiceGUI → TXT/SRT/JSON/DOCX file download`

Stages:

1. **Ingestion** — `YouTubeHandler` validates the URL via a regex covering `youtube.com/watch`, `youtu.be/`, `/shorts/`, `/embed/`, `/v/`. yt-dlp downloads to `downloads/{job_id}/`.
2. **Audio extraction** — `AudioExtractor` shells to FFmpeg and produces a normalized 16 kHz mono WAV optimized for Whisper.
3. **Transcription** — `TranscriptionEngine` wraps faster-whisper with lazy model loading. Segments include `start_time`, `end_time`, `text`, and `confidence`.
4. **Persistence** — `TranscriptRepository` writes `jobs` and `transcripts` rows to SQLite. Segments serialize to JSON in a single `segments_json` column for schema flexibility. All writes serialize through a `threading.RLock`.
5. **Retrieval** — FastAPI routes expose status polling and transcript fetch. The UI polls every 3 seconds via NiceGUI `ui.timer`.
6. **Export** — Pure functions in `exports/` take a `Transcript` and return `str` or `bytes`. No I/O inside exporters.

The pipeline is single-host by design. No queue broker, no cloud storage, no message bus.

---

## Frontend

| Attribute | Value |
|---|---|
| Framework | NiceGUI (Python-native, no separate JS build) |
| Theme | Dark mode, centralized NTH color palette in [ui/colors.py](ui/colors.py) — 11 hex constants, no hardcoded colors in panels |
| Layout | Three-column responsive grid: Submission \| History \| Transcript Viewer |
| Panels | 3 — [job_submission_panel.py](ui/panels/job_submission_panel.py), [history_panel.py](ui/panels/history_panel.py), [transcript_viewer_panel.py](ui/panels/transcript_viewer_panel.py) |
| State management | Panel-local instance variables; cross-panel wiring via `on_job_complete` / `on_select` callbacks in [ui/app.py](ui/app.py) |
| API boundary | httpx only — no direct imports from `ingestion/`, `transcription/`, `storage/`, or `exports/` into any UI file (enforced by Frontend Agent hard rule) |
| Accessibility | TBD — no a11y tooling wired. Action item: add an axe-core or Lighthouse pass in a future sprint. |

The UI is functional and operator-grade. It is not, at this stage, a design-system-compliant product surface. Polish is tracked for a later sprint.

---

## Backend

| Attribute | Value |
|---|---|
| API framework | FastAPI + uvicorn |
| Endpoints | 5 — `POST /jobs`, `GET /jobs`, `GET /jobs/{id}`, `GET /jobs/{id}/transcript`, `GET /jobs/{id}/transcript/export` |
| Interactive docs | Swagger UI at `/docs`, ReDoc at `/redoc` (FastAPI default) |
| Auth | None — local-only / air-gapped by design. No auth surface means no auth attack surface. |
| ORM | Raw `sqlite3` stdlib with a hand-rolled repository. No SQLAlchemy, no Prisma. |
| Background jobs | Python `threading.Thread(daemon=True)` via `JobProcessor`. No Celery, no RQ, no Redis. |
| Concurrency primitive | `threading.RLock()` on every write path in the repository |
| Config | `python-dotenv` reading [.env.example](.env.example). No hardcoded paths. |
| Logging | stdlib `logging`, module-level `logger = logging.getLogger(__name__)` |
| Paths | `pathlib.Path` throughout — enforced as a backend-agent hard rule for Windows compatibility |

The backend is deliberately boring. Boring scales, boring audits cleanly, boring hands off to any Python developer without a week of ramp-up.

---

## QA / QC Regime

| Attribute | Value |
|---|---|
| Test framework | pytest + pytest-mock + pytest-asyncio + FastAPI TestClient |
| Total tests | 58 |
| Test LOC | 903 (34% of total Python) |
| Test files | 5 (one per sprint + `__init__.py`) |
| Coverage tooling | Not wired — action item. Test-to-source LOC ratio used as proxy. |
| Hard gates per sprint | Each sprint designates 2–3 sprint-halting tests that must pass before the full suite runs. Example: Sprint 2's `test_repository_save_and_get_job`, `test_api_submit_job_valid_url`, `test_api_get_transcript_complete`. |
| Frozen-asset gate | `git diff --name-only HEAD` run before every commit. PM Agent halts the sprint if anything outside the explicit allowlist shows as modified. |
| Linting / formatting | Not wired — action item. Observed style is consistent by convention, not by tool. |
| Definition of Done | Every sprint has an explicit, copy-pasted DoD checklist in its master doc. PM Agent walks every line before issuing the commit. |

**What QA owns that backend does not:** every test file. The backend agent writes zero test code by policy. This produces an adversarial check — the QA agent reads the sprint spec and builds tests from requirements, not from the implementation.

---

## CI / CD

Not wired. No `.github/workflows/`, no `.gitlab-ci.yml`, no Azure Pipelines config.

Current "CI" is the PM Agent's DoD gate: full test suite + frozen-asset `git diff` + import verification runs locally before every commit. The six commits on `main` all cleared this gate.

**Action item:** wire a GitHub Actions workflow that runs `pytest tests/ -v` on push + PR. Cost: under an hour. Deferred because the project has been single-operator with 100% local test discipline — the ROI comes when a second contributor lands.

---

## Governance

| Dimension | Observed Evidence |
|---|---|
| IP ownership | Repo private under `robcushard-nth`. No LICENSE file yet — action item. Claim: NTH AI Dynamics / NTH Simple Solution Corp proprietary. |
| ADRs | No formal `docs/adr/` directory. Architecture decisions are embedded in the sprint master docs (e.g., "Pydantic schemas live in API layer only; never redefine `models/transcript.py`"). |
| CODEOWNERS | Not present — sole operator. |
| Documentation index | [README.md](README.md) (developer) + [USER_GUIDE.md](USER_GUIDE.md) (end-user) + [portfolio.md](portfolio.md) (this file, executive) + four [CLAUDE_MASTER_SPRINT_*.md](.claude/agents) specs. |
| Commit discipline | Every commit uses the `sprint{N}: {module} complete` or `docs:` convention. No "wip", no "fix stuff" commits. |

---

## Scalability

This is a **single-host, single-operator** tool by current design. The scalability posture reflects that intentionally.

| Concern | Current State | Path to Scale |
|---|---|---|
| Concurrent jobs | 1 daemon thread per submission; unbounded spawn | Add a bounded ThreadPoolExecutor or swap to a proper queue (RQ/Celery) once N operators hit the box. |
| Data volume | SQLite file on local disk | Swap repository implementation for Postgres; schema is already JSON-flexible. |
| Long videos | Memory-bound by Whisper model choice + CPU | Chunk long audio in the engine; already natural boundary in `TranscriptSegment`. |
| Model-weight cache | faster-whisper default cache in user profile | Pre-seed a shared volume if multi-user. |
| Horizontal scale | Not applicable at current scope | Front with a job queue; repository already thread-safe. |

The architecture does not block scale — the repository interface is narrow, the pipeline is staged, and the models are frozen. Scaling is a swap of concrete implementations behind stable interfaces.

---

## Security

| Concern | Posture |
|---|---|
| Data sovereignty | **Audio never leaves the host.** No third-party transcription API. yt-dlp calls YouTube; everything after that is local. |
| Secrets handling | No API keys required for core function. `.env` carries only runtime knobs (model, device, compute type, paths). `.env` is gitignored; `.env.example` is committed. |
| Auth | None. The app binds to `0.0.0.0` by default — deployers should bind to `127.0.0.1` or put it behind a local reverse proxy if the host is multi-user. Action item: add a config flag for `127.0.0.1` default. |
| Encryption at rest | None — SQLite file is plain. Acceptable for a local single-operator build; not acceptable for a regulated multi-user deployment. |
| Encryption in transit | None — HTTP, not HTTPS. Same scope caveat. |
| Input validation | URL validation regex in [ingestion/youtube_handler.py](ingestion/youtube_handler.py) rejects non-YouTube patterns with a 400 before any shell-out. |
| Shell injection | FFmpeg invocation uses list-args (not `shell=True`). |
| Dependency scanning | Not wired — action item. Deps pinned by `>=`; upgrade discipline is manual. |
| Compliance posture | **Compatible by architecture, not certified.** The sovereign-stack design (no external API, no cloud transit) is consistent with ITAR, CMMC L2, HIPAA, NDAA FY2026 §1532, and NDA-bound client work. Formal certification TBD per engagement. |

---

## AI Architecture

| Dimension | Value |
|---|---|
| Model | OpenAI Whisper family via faster-whisper (CTranslate2 backend). Operator-selectable: `tiny`, `base`, `small`, `medium`, `large-v3`. |
| Deployment | **100% local / sovereign.** No Ollama server, no API endpoint, no cloud inference. Model weights cache to the user profile on first use. |
| Device | CPU (`int8` quantization) by default; CUDA (`float16`) supported via env var. |
| Tool-calling / MCP | Not applicable — this is a single-task pipeline, not an agentic runtime. |
| RAG | Not applicable — transcription is source-to-text, not retrieval. |
| Prompt engineering | Not applicable for transcription itself. Prompt engineering IS applied in the operator-facing delivery pipeline: four Claude Code agents running against hand-authored sprint master docs. |
| Context management | N/A for Whisper. For the delivery agents: each sprint's master doc is the context window's anchor; PM Agent rehydrates it at every phase. |
| Guardrails | URL allowlist (YouTube-only at Sprint 4). File-size / duration limits TBD. |

**Key architectural claim:** this build demonstrates that a production-usable AI application can ship with zero third-party AI API calls. Every decision — faster-whisper over OpenAI's hosted Whisper, SQLite over a managed DB, NiceGUI over a React SPA with a cloud auth broker — compounds the sovereignty posture.

---

## Proprietary IP Applied

Explicit mapping against NTH frameworks:

| Framework | Applied? | How |
|---|---|---|
| **Four-Agent Sprint Pattern™** (PM / Backend / Frontend / QA) | ✅ Yes — canonical | Four agent specs in [.claude/agents/](.claude/agents), enforced role separation, frozen-file verification, per-sprint DoD. This build is a reference implementation of the pattern. |
| **Intelligent Operations System™ (IOS)** — sovereign AI stack | ✅ Partially | Local-only Whisper inference and SQLite persistence. Does not yet include Qdrant / n8n / Open WebUI / ZeroClaw — those apply to RAG-centric IOS builds, not this single-task pipeline. |
| **CI 4.0™** — continuous-improvement-as-substrate | ✅ Via sprint reshuffle | The Sprint 4/5 reshuffle (export engine pulled forward, multi-source deferred) is a documented CI 4.0 move: the roadmap serves the operator's workflow, not the original Gantt chart. |
| **Modern Command Framework™ (MCF)** — decision-rights patterns | ⚪ Low direct use | Agent role separation is MCF-shaped (each agent has a bounded decision scope), but MCF's broader C2 applications don't map to a single-app build. |
| **Leadership as a System™ (LaS)** | ⚪ Not applicable | LaS applies to human-system design; this is a tool build. |
| **Two-Layer IP Protection Architecture** (for NDA-bound client work) | ⚪ Not applicable | Internal product, single operator. |

**Non-framework techniques worth naming:**
- Pure-function exporters ([exports/*.py](exports)) with zero I/O — makes unit testing trivial and keeps the DB/API layers the sole persistence surface.
- JSON-column segment storage in SQLite — sidesteps segment-schema migration churn while keeping SQL-level queryability on the parent `transcripts` row.
- httpx-only API boundary for the UI — the frontend has zero coupling to the transcription stack, which means the UI could be swapped for a CLI, a Streamlit app, or a React SPA with no backend changes.

---

## Industry Context

| Dimension | Value |
|---|---|
| Vertical | **Cross-vertical.** Built for any operations context where transcripts are a work product: manufacturing (shop-floor training videos), legal (deposition audio), financial services (analyst calls), government / defense (briefings), home services (customer calls), healthcare (clinician dictation). |
| Regulatory environment | Designed compatible with ITAR, CMMC L2, HIPAA, NDAA FY2026 §1532, SOC 2 posture. Certification is per-engagement. |
| Stakeholder audience | Primary: operators (ops managers, analysts, fractional COOs). Secondary: engineering (for extension), compliance (for audit). |
| Engagement model | NTH internal product — reference build for sovereign AI stack. Not a client deliverable. Reusable as a case study in proposals for regulated clients who cannot ship audio to third parties. |

---

## Measurable Outcomes

- **Delivery velocity:** 4 sprints × ~3.5 calendar days per sprint = operator-usable app in 14 days.
- **Test coverage proxy:** 58 tests, 903 test LOC, 34% test-to-source LOC ratio, zero test code written by the agent that wrote the source.
- **Frozen-file discipline:** 4 sprints, 0 unauthorized modifications to frozen files. Every sprint-4 modification to a prior-sprint file was against an explicit one-line allowlist.
- **Commit hygiene:** 6 commits, 100% conform to `sprint{N}: ... complete` or `docs: ...` convention. Zero "wip" or "fix" commits on `main`.
- **Sovereignty:** 0 third-party AI API calls in the transcription pipeline. 1 third-party dependency with external network reach (yt-dlp → YouTube), scoped to the ingestion stage only.
- **Operator-readiness:** `pip install -r requirements.txt`, `uvicorn api.main:app`, `python -m ui.app`, open `http://localhost:8080`, paste URL, click Transcribe. End-to-end in a browser, no terminal round-tripping.

---

## Known Gaps / Action Items

Captured here so they are not rediscovered:

- `TBD — LICENSE file and explicit IP declaration in repo root`
- `TBD — GitHub Actions CI wired to run pytest on push/PR`
- `TBD — coverage tooling (pytest-cov) with a minimum-coverage gate`
- `TBD — linting (ruff) + formatter (black) + pre-commit hooks`
- `TBD — accessibility pass on the NiceGUI dashboard`
- `TBD — bind default to 127.0.0.1 with an explicit opt-in for 0.0.0.0`
- `TBD — Sprint 5: multi-source ingestion (local file, direct URL, Vimeo)`
- `TBD — optional at-rest encryption for SQLite when deployed multi-user`
- `TBD — dependency-vulnerability scanning (pip-audit or Dependabot)`

---

## Data Sources

Every metric in this document is reproducible from the repo at commit `9724672`:

- **File and LOC counts:** `find . -type f -name "*.py" ... | xargs wc -l`
- **Commits and dates:** `git log --reverse --format="%ai"`, `git rev-list --count HEAD`
- **Test counts:** `grep -c "^def test_" tests/test_sprint*.py`
- **Tech stack:** [requirements.txt](requirements.txt) pin list
- **Agent structure:** [.claude/agents/](.claude/agents) directory listing + per-agent file headers
- **Sprint history:** `git log --oneline` + [.claude/agents/CLAUDE_MASTER_SPRINT_*.md](.claude/agents)
- **Endpoints:** route decorators in [api/routes/jobs.py](api/routes/jobs.py) and [api/routes/exports.py](api/routes/exports.py)

---

## Contact

**Rob Cushard** | NTH AI Dynamics / NTH Simple Solution Corp
rob.cushard@nthsimplesolution.com | 470-426-4144
