# JSON Screen App (Flask skeleton)

## Ubuntu server deployment

Verified on **14 September 2026** against the listeners, user systemd services,
Docker port mappings and deployment registry on `192.168.1.249`.

| Endpoint | Host TCP port | LAN URL |
|---|---:|---|
| Application | 5064 | http://192.168.1.249:5064/ |

Checkout: `/home/zageabb/flask/ScreenDesign`.

These are **user** systemd units. Inspect them with:

```bash
systemctl --user status migrated-flask@ScreenDesign.service
systemctl --user cat migrated-flask@ScreenDesign.service
```

Local verification URL: `http://127.0.0.1:5064/`. HTTP 200 was observed during this audit.

Development defaults and container-internal ports elsewhere in this repository
may differ from this host deployment. Use the live ports above when accessing
this Ubuntu server; do not start a second copy on a port already occupied.

[Complete Ubuntu port inventory](https://github.com/zageabb/universal-deployment-agent/blob/main/UBUNTU_PORTS.md).

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

