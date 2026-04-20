# Backend Agent — NTH Transcript Engine Sprint 3

## Role
Sprint 3 is a frontend sprint. Your role is limited to one task:
append `nicegui>=1.4.0` to `requirements.txt` and confirm installation.

Do not modify any other files. Do not write UI code. Do not write tests.

---

## Sprint 3 Backend Task: Update requirements.txt

Open `requirements.txt` and append this line at the bottom:
```
nicegui>=1.4.0
```

Then install:
```bash
pip install -r requirements.txt
```

Verify:
```bash
python -c "import nicegui; print(f'NiceGUI installed: {nicegui.__version__}')"
```

Report to PM Agent: NiceGUI version confirmed, requirements.txt updated.

---

## Frozen Assets — Sprint 3
Everything except `requirements.txt` is frozen.
Do not touch `models/`, `ingestion/`, `transcription/`, `storage/`, `api/`, or any test files.

---

## Post-Sprint Reference for Sprint 4

Sprint 4 (Multi-Source) will add to backend:
- `ingestion/local_file_handler.py` — handles .mp4, .mov, .avi, .mkv local files
- `ingestion/url_handler.py` — handles direct video URLs (not YouTube-specific)
- New API endpoint: `POST /jobs/upload` — accepts multipart file upload
- Sprint 4 appends: `python-multipart>=0.0.9` to requirements.txt

Sprint 4 must prepend full regression: `pytest tests/ -v` (40 tests) before any new code.
