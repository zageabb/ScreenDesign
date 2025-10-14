# JSON Screen App (Flask skeleton)

A dynamic, JSON‑driven screen system:
- Screens are defined by JSON schemas in `./screens/*.json`.
- Records are stored as a single JSON object in SQLite (`Record.data_json`).
- Adding new fields won't break old records: on load, defaults from schema are merged; on save, full shape is written.
- Safe declarative rules (show/hide/lock) are evaluated server‑side and also in the client for live UX.
- Sub‑screens inherit main properties and link back to the parent via `parent_id`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export FLASK_APP=app.py  # Windows: set FLASK_APP=app.py
flask --app app.py db-init
flask --app app.py load-schemas
flask --app app.py run --debug --port 5004
```

Open `http://127.0.0.1:5004/screen/vehicle`

## Structure

- `app.py` – Flask routes + CLI
- `models.py` – SQLAlchemy models (Schema, Record)
- `schema_loader.py` – loads/merges JSON schemas from `./screens`
- `rules.py` – tiny safe expression evaluator (AST whitelist)
- `storage.py` – schema‑aware CRUD helpers
- `templates/` – Jinja templates: `base.html`, `screen_form.html`, `screen_list.html`
- `static/js/renderer.js` – client‑side rule application
- `screens/examples/vehicle.json`, `screens/examples/service.json` – sample screens
- `tests/` – smoke tests for rules + merge

