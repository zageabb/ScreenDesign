from __future__ import annotations
import os, json
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from models import init_db, SessionLocal, Schema
from schema_loader import (
    load_schemas,
    get_schema,
    get_schema_meta,
    list_schema_metadata,
    SCREENS_DIR,
)
from storage import (
    list_records,
    save_record,
    merge_defaults,
    compute_rules,
    get_record,
    delete_record,
    get_record_raw,
    update_record,
    recompute_preview,
)

STAGING_DIR = os.path.join(SCREENS_DIR, "staging")

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
    template_name = "screen_edit_form.html" if record_id else "screen_form.html"
    return render_template(template_name, schema=schema, defaults=defaults, record_id=record_id)

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


@app.post("/screen/<slug>/update/<int:record_id>")
def screen_update(slug: str, record_id: int):
    schema = get_schema(slug)
    if not schema:
        abort(404)
    raw_data = request.json if request.is_json else request.form.to_dict()
    data = dict(raw_data) if isinstance(raw_data, dict) else raw_data
    parent_id = request.args.get("parent_id")
    parent_id = int(parent_id) if parent_id else None
    if isinstance(data, dict):
        data.pop("id", None)
    try:
        rec_id = update_record(slug, record_id, data, parent_id=parent_id)
    except ValueError:
        abort(404)
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


@app.post("/screen/<slug>/recompute")
def screen_recompute(slug: str):
    schema = get_schema(slug)
    if not schema:
        abort(404)
    raw_data = request.json if request.is_json else request.form.to_dict()
    if not isinstance(raw_data, dict):
        abort(400)
    payload = dict(raw_data)
    payload.pop("id", None)
    try:
        data = recompute_preview(slug, payload)
    except ValueError:
        abort(404)
    return jsonify({"data": data})


def ensure_staging_dir() -> None:
    os.makedirs(STAGING_DIR, exist_ok=True)


@app.get("/admin/")
def admin_index():
    forms_meta = list_schema_metadata()
    forms = []
    for slug, meta in sorted(forms_meta.items()):
        schema = get_schema(slug) or {}
        forms.append(
            {
                "slug": slug,
                "title": schema.get("title") or meta.get("title") or slug,
                "rel_path": meta.get("rel_path"),
                "read_only": bool(meta.get("read_only")),
            }
        )
    message = request.args.get("message")
    error = request.args.get("error")
    return render_template("admin/index.html", forms=forms, message=message, error=error)


@app.route("/admin/form/<slug>", methods=["GET", "POST"])
def admin_edit_form(slug: str):
    meta = get_schema_meta(slug)
    if not meta:
        abort(404)
    message = request.args.get("message")
    error = None
    raw_text = ""
    if request.method == "POST":
        if meta.get("read_only"):
            abort(403)
        raw_text = request.form.get("schema_json", "").strip()
        try:
            data = json.loads(raw_text or "{}")
        except json.JSONDecodeError as exc:
            error = f"Invalid JSON: {exc}"
        else:
            data["slug"] = slug
            with open(meta["path"], "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            load_schemas()
            return redirect(url_for("admin_edit_form", slug=slug, message="Changes saved."))
    if not raw_text:
        with open(meta["path"], "r", encoding="utf-8") as f:
            raw_text = f.read()
    return render_template(
        "admin/edit_form.html",
        slug=slug,
        schema_json=raw_text,
        read_only=bool(meta.get("read_only")),
        message=message,
        error=error,
        rel_path=meta.get("rel_path"),
    )


@app.get("/admin/form/<slug>/records")
def admin_form_records(slug: str):
    schema = get_schema(slug)
    if not schema:
        abort(404)
    meta = get_schema_meta(slug) or {}
    page_param = request.args.get("page", "1")
    try:
        page = max(int(page_param), 1)
    except ValueError:
        page = 1
    page_size = 20
    parent_id_raw = request.args.get("parent_id")
    parent_id = None
    conversion_error = None
    if parent_id_raw:
        try:
            parent_id = int(parent_id_raw)
        except ValueError:
            conversion_error = "Parent ID must be an integer."
    rows, total = list_records(slug, parent_id=parent_id, page=page, page_size=page_size)
    columns = schema.get("columns") or [f.get("name") for f in schema.get("fields", []) if f.get("name")]
    total_pages = max((total + page_size - 1) // page_size, 1)
    message = request.args.get("message")
    error = request.args.get("error") or conversion_error
    return render_template(
        "admin/form_records.html",
        schema=schema,
        meta=meta,
        rows=rows,
        columns=columns,
        total=total,
        page=page,
        total_pages=total_pages,
        page_size=page_size,
        parent_id=parent_id,
        message=message,
        error=error,
    )


@app.route("/admin/form/<slug>/record/<int:record_id>", methods=["GET", "POST"])
def admin_record_detail(slug: str, record_id: int):
    schema = get_schema(slug)
    if not schema:
        abort(404)
    meta = get_schema_meta(slug)
    if not meta:
        abort(404)
    read_only = bool(meta.get("read_only"))
    record = get_record_raw(record_id, screen_slug=slug)
    if not record:
        abort(404)
    message = request.args.get("message")
    error = None
    raw_text = record["data_json"] or "{}"
    pretty_text = None
    if record.get("data") is not None:
        pretty_text = json.dumps(record["data"], indent=2, ensure_ascii=False)
    parent_id_value = "" if record["parent_id"] is None else str(record["parent_id"])
    if request.method == "POST":
        action = request.form.get("action") or "save"
        if action == "delete":
            if read_only:
                abort(403)
            delete_record(record_id, screen_slug=slug)
            return redirect(url_for("admin_form_records", slug=slug, message="Record deleted."))
        if read_only:
            abort(403)
        raw_text_input = request.form.get("record_json", "")
        raw_text = raw_text_input
        parent_id_raw = request.form.get("parent_id", "").strip()
        if not raw_text_input.strip():
            raw_text = "{}"
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            error = f"Invalid JSON: {exc}"
        else:
            parent_id = None
            if parent_id_raw:
                try:
                    parent_id = int(parent_id_raw)
                except ValueError:
                    error = "Parent ID must be blank or an integer."
            if error is None:
                save_record(slug, data, parent_id=parent_id, record_id=record_id)
                return redirect(url_for("admin_record_detail", slug=slug, record_id=record_id, message="Record updated."))
            parent_id_value = parent_id_raw
    else:
        raw_text = pretty_text or raw_text
    return render_template(
        "admin/record_detail.html",
        schema=schema,
        meta=meta,
        record=record,
        read_only=read_only,
        raw_json_text=raw_text,
        parent_id_value=parent_id_value,
        message=message,
        error=error,
    )


@app.route("/admin/new", methods=["GET", "POST"])
def admin_new_form():
    default_json = json.dumps(
        {
            "slug": "",
            "title": "New Form",
            "fields": [],
        },
        indent=2,
    )
    error = None
    slug = ""
    schema_json = default_json
    if request.method == "POST":
        slug = (request.form.get("slug") or "").strip()
        schema_json = request.form.get("schema_json", "").strip() or default_json
        if not slug:
            error = "Slug is required."
        elif not all(c.isalnum() or c in {"_", "-"} for c in slug):
            error = "Slug may only contain letters, numbers, underscores, or hyphens."
        else:
            load_schemas()
            if slug in list_schema_metadata():
                error = "A form with this slug already exists."
        if not error:
            try:
                data = json.loads(schema_json)
            except json.JSONDecodeError as exc:
                error = f"Invalid JSON: {exc}"
            else:
                data["slug"] = slug
                ensure_staging_dir()
                path = os.path.join(STAGING_DIR, f"{slug}.json")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                load_schemas()
                return redirect(url_for("admin_edit_form", slug=slug, message="Form created."))
    return render_template(
        "admin/new_form.html",
        slug=slug,
        schema_json=schema_json,
        error=error,
    )

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5004)
