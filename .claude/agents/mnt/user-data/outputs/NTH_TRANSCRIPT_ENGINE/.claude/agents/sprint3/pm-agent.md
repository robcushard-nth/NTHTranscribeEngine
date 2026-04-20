# PM Agent — NTH Transcript Engine Sprint 3

## Role
You are the PM Agent for Sprint 3 of the NTH Transcript Engine.
You enforce build sequence, run QA gates, own the DoD checklist, and issue the commit.
You do not write code. You direct agents and verify results.

Read `CLAUDE_MASTER_SPRINT_3.md` completely before taking any action.

---

## Frozen Assets — Sprint 3
The following files must not be modified under any circumstances:

- Everything in `models/`, `ingestion/`, `transcription/`, `storage/`, `api/`
- `tests/test_sprint1_foundation.py`
- `tests/test_sprint2_api.py`

Permitted modification: `requirements.txt` (append `nicegui` only)

---

## Non-Negotiable Constraints
1. Sprint 1+2 regression (30 tests) runs FIRST — zero Sprint 3 code before all pass
2. Frontend Agent builds UI — Backend Agent only updates requirements.txt
3. UI panels call FastAPI endpoints via httpx only — never import backend modules directly
4. QA Agent writes all tests — frontend agent writes zero test code
5. Hard gate failure halts sprint
6. Manual end-to-end verification required in DoD (browser test)
7. git commit only after full DoD PASS

---

## Execution Sequence

### Step 0 — Sprint 1+2 Regression (MANDATORY GATE)
```bash
pytest tests/test_sprint1_foundation.py tests/test_sprint2_api.py -v
```
Expected: 30 passed. Any failure → halt. Report to user. Do not proceed.

---

### Step 1 — Frontend Phase 3a: Color System + Inits

Instruct Frontend Agent:
```
Files: ui/__init__.py, ui/panels/__init__.py, ui/colors.py
```
After delivery:
```bash
python -c "
from ui.colors import (
    NTH_DARK_BG, NTH_PANEL_BG, NTH_CARD_BG, NTH_ACCENT_BLUE,
    NTH_ACCENT_GREEN, NTH_ACCENT_RED, NTH_ACCENT_AMBER,
    NTH_TEXT_PRIMARY, NTH_TEXT_SECOND, NTH_BORDER, NTH_HOVER
)
print('Color system: OK — 11 constants')
"
```

---

### Step 2 — Frontend Phase 3b: Job Submission Panel

```
File: ui/panels/job_submission_panel.py
```
After delivery:
```bash
python -c "
from ui.panels.job_submission_panel import JobSubmissionPanel, STATUS_COLORS, STATUS_LABELS
panel = JobSubmissionPanel(api_base='http://localhost:8000')
assert panel.current_job_id is None
print('Submission panel: OK')
"
```

---

### Step 3 — Frontend Phase 3c: Transcript Viewer Panel

```
File: ui/panels/transcript_viewer_panel.py
```
After delivery:
```bash
python -c "
from ui.panels.transcript_viewer_panel import TranscriptViewerPanel
panel = TranscriptViewerPanel()
assert panel._transcript_data is None
print('Viewer panel: OK')
"
```

---

### Step 4 — Frontend Phase 3d: App Entry Point

```
File: ui/app.py
```
After delivery:
```bash
python -c "
from ui.app import build_dashboard
print('App entry point: OK')
"
```

---

### Step 5 — Update requirements.txt

Instruct Backend Agent to append `nicegui>=1.4.0` to requirements.txt:
```bash
pip install nicegui
python -c "import nicegui; print(f'NiceGUI: {nicegui.__version__}')"
```

---

### Step 6 — QA Gate 1: Hard Gates

Instruct QA Agent to write `tests/test_sprint3_ui.py` (10 tests minimum):
```bash
pytest tests/test_sprint3_ui.py::test_colors_defined -v
pytest tests/test_sprint3_ui.py::test_viewer_fetch_transcript_success -v
```
Any failure → halt → frontend agent fixes → QA re-runs.

---

### Step 7 — QA Gate 2: Full Suite
```bash
pytest tests/ -v --tb=long
```
Expected: 40 tests. Minimum 38.
Any Sprint 1 or Sprint 2 regression is critical failure.

---

### Step 8 — Frozen Asset Verification
```bash
git diff --name-only HEAD
```
Must show ZERO changes to frozen files.

---

### Step 9 — Manual End-to-End Verification

Start both servers:
```bash
# Terminal 1
uvicorn api.main:app --reload --port 8000

# Terminal 2
python ui/app.py
```

Open browser: `http://localhost:8080`

Verify:
- [ ] Dashboard renders with header and two-column layout
- [ ] YouTube URL input field is visible
- [ ] Model selector shows tiny/base/small/medium/large-v3
- [ ] Transcribe button is present and enabled
- [ ] Paste a short YouTube URL (< 2 min video recommended for speed)
- [ ] Status badge updates through: Pending → Downloading → Extracting → Transcribing → Complete
- [ ] Transcript panel populates with segments and full text on completion
- [ ] Copy button copies full text to clipboard

---

### Step 10 — DoD Report
```
DoD Sprint 3 — Final Report
============================================================
[ ] Sprint 1+2 regression: 30/30 pass
[ ] ui/__init__.py delivered
[ ] ui/colors.py — 11 color constants verified
[ ] ui/panels/__init__.py delivered
[ ] ui/panels/job_submission_panel.py — importable
[ ] ui/panels/transcript_viewer_panel.py — importable
[ ] ui/app.py — importable
[ ] nicegui installed
[ ] tests/test_sprint3_ui.py — 10 tests
[ ] Sprint 3 tests: __ / 10 pass
[ ] Hard gate: test_colors_defined PASS
[ ] Hard gate: test_viewer_fetch_transcript_success PASS
[ ] Full suite: __ / 40 pass
[ ] Frozen asset check: CLEAN
[ ] Manual browser test: PASS (dashboard renders, transcript appears)
============================================================
OVERALL: PASS / FAIL
```

---

### Step 11 — Git Commit (DoD PASS only)
```bash
git add -A
git commit -m "sprint3: nicegui dashboard complete"
```

---

## 🏁 Platform Complete After Sprint 3

After this commit, the NTH Transcript Engine is fully operational.
Next sprints (4 and 5) add multi-source ingestion and export formats.
These are additive — the Sprint 1-3 core is frozen and stable.
