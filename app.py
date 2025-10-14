from __future__ import annotations
import os, json
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from models import init_db, SessionLocal, Schema
from schema_loader import load_schemas, get_schema
from storage import list_records, save_record, merge_defaults, compute_rules, get_record, delete_record

app = Flask(__name__)

# Ensure the database schema exists before handling any requests or CLI commands.
init_db()

@app.cli.command("db-init")
def db_init():
    init_db()
    print("DB initialized.")

@app.cli.command("load-schemas")
def cli_load_schemas():
    schemas = load_schemas()
    from models import SessionLocal, Schema
    with SessionLocal() as db:
        for slug, sch in schemas.items():
            obj = db.query(Schema).filter(Schema.slug == slug).first()
            raw = json.dumps(sch)
            if obj:
                obj.version = sch.get("version", obj.version or 1)
                obj.json = raw
            else:
                obj = Schema(slug=slug, version=sch.get("version", 1), json=raw)
                db.add(obj)
        db.commit()
    print(f"Loaded {len(schemas)} schema(s) into DB.")

@app.get("/")
def index():
    # List available schemas
    schemas = load_schemas()
    return render_template("index.html", schemas=schemas)

@app.get("/screen/<slug>")
def screen(slug: str):
    schema = get_schema(slug)
    if not schema: abort(404)
    mode = schema.get("mode", "form")  # or "list"
    force_form = bool(request.args.get("form") == "1" or request.args.get("new") == "1" or request.args.get("id"))
    if request.args.get("list") == "1":
        show_list = True
    elif request.args.get("list") == "0":
        show_list = False
    else:
        show_list = mode == "list" and not force_form
    if show_list:
        page = int(request.args.get("page", 1))
        parent_id = request.args.get("parent_id")
        parent_id = int(parent_id) if parent_id else None
        rows, total = list_records(slug, parent_id=parent_id, page=page, page_size=20)
        columns = schema.get("columns") or [f.get("name") for f in schema.get("fields", [])]
        return render_template("screen_list.html", schema=schema, rows=rows, columns=columns, total=total, page=page, parent_id=parent_id)
    # default form
    rec_id = request.args.get("id")
    record_id = None
    record_data = {}
    if rec_id:
        record_id = int(rec_id)
        record_data = get_record(record_id, screen_slug=slug)
        if record_data is None:
            abort(404)
    defaults = merge_defaults(schema, record_data)
    return render_template("screen_form.html", schema=schema, defaults=defaults, record_id=record_id)

@app.post("/screen/<slug>/save")
def screen_save(slug: str):
    schema = get_schema(slug)
    if not schema: abort(404)
    raw_data = request.json if request.is_json else request.form.to_dict()
    data = dict(raw_data) if isinstance(raw_data, dict) else raw_data
    parent_id = request.args.get("parent_id")
    parent_id = int(parent_id) if parent_id else None
    rec_id_param = request.args.get("id")
    if not rec_id_param and isinstance(raw_data, dict):
        rec_id_param = raw_data.get("id")
    if isinstance(data, dict):
        data.pop("id", None)
    record_id = int(rec_id_param) if rec_id_param else None
    try:
        rec_id = save_record(slug, data, parent_id=parent_id, record_id=record_id)
    except ValueError:
        abort(404)
    # redirect to list view if child list expected, else back to form
    next_location = None
    if request.args.get("next") == "list":
        next_location = url_for("screen", slug=slug, list=1, parent_id=parent_id)
    if request.is_json:
        payload = {"ok": True, "id": rec_id}
        if next_location:
            payload["redirect"] = next_location
        return jsonify(payload)
    if next_location:
        return redirect(next_location)
    return redirect(url_for("screen", slug=slug, id=rec_id))

@app.post("/screen/<slug>/delete/<int:record_id>")
def screen_delete(slug: str, record_id: int):
    parent_id = request.args.get("parent_id")
    parent_id = int(parent_id) if parent_id else None
    try:
        delete_record(record_id, screen_slug=slug)
    except ValueError:
        abort(404)
    next_kwargs = {"slug": slug, "list": 1}
    if parent_id is not None:
        next_kwargs["parent_id"] = parent_id
    next_location = url_for("screen", **next_kwargs)
    if request.is_json:
        payload = {"ok": True}
        if next_location:
            payload["redirect"] = next_location
        return jsonify(payload)
    return redirect(next_location)

@app.post("/rules/<slug>")
def rules(slug: str):
    ctx = request.json or {}
    result = {k: list(v) for k, v in compute_rules(slug, ctx).items()}
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5004)
