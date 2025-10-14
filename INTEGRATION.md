# Integrating with `Flask_Question`

This bundle is tailored to the repository structure you shared.

- **Schema directory:** defaults to `forms/` (set `SCREENS_DIR=forms`).
- **Templates & static:** lives alongside existing `templates/` and `static/`.
- **Computed fields:** add `"compute": "qty * cost"` to any field (top-level or group subfield).
  - The browser calculates values live for UX.
  - The server **recomputes** on save to enforce correctness.

## Copy-in steps

1. Drop these files/folders into your repo root:
   - `schema_loader.py`, `storage.py`, `rules.py`, `models.py`, `app.py` (or merge routes into your existing `app.py`)
   - `templates/` (merge), `static/js/renderer.js` (merge)
   - `forms/examples/*.json` (or move into your `forms/` folder)
2. Ensure dependencies in `requirements.txt`: Flask, SQLAlchemy, python-dateutil.
3. Run:
   ```bash
   flask --app app.py db-init
   flask --app app.py load-schemas
   flask --app app.py run --debug
   ```
4. Open: `/screen/vehicle`

## Notes

- The loader now points at `forms/` to align with the repo.
- Existing `template_loader.py` can coexist; this system reads JSON and renders dynamically.
- You can use `$extends` in form JSONs to inherit a base screen.
- For repeatable tables, data persists as arrays of objects; schema evolution is handled by merging defaults on load.

