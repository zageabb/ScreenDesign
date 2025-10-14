from __future__ import annotations
import json
from datetime import UTC, datetime
from typing import Any, Dict, Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from models import SessionLocal, Record, Schema
from schema_loader import get_schema
from rules import apply_rules

def _defaults_from_schema(schema: dict) -> Dict[str, Any]:
    d = {}
    for f in schema.get("fields", []):
        ftype = f.get("type")
        name = f.get("name")
        if not name:
            continue
        if ftype == "group" and f.get("mode") == "repeatable-table":
            d[name] = f.get("default", [])
        else:
            if f.get("default") is not None:
                d[name] = f["default"]
            else:
                d[name] = None
    return d

def merge_defaults(schema: dict, data: Dict[str, Any]) -> Dict[str, Any]:
    base = _defaults_from_schema(schema)
    result = {**base, **(data or {})}
    for f in schema.get("fields", []):
        if f.get("type") == "group" and f.get("mode") == "repeatable-table":
            rows = result.get(f["name"]) or []
            fixed_rows = []
            sub_defaults = {}
            for sf in f.get("fields", []):
                sub_defaults[sf["name"]] = sf.get("default", None)
            for r in rows:
                rr = {**sub_defaults, **(r or {})}
                fixed_rows.append(rr)
            result[f["name"]] = fixed_rows
    return result

def list_records(screen_slug: str, parent_id: Optional[int]=None, page:int=1, page_size:int=20) -> Tuple[List[Dict[str, Any]], int]:
    with SessionLocal() as db:
        stmt = select(Record).where(Record.screen_slug == screen_slug)
        if parent_id is not None:
            stmt = stmt.where(Record.parent_id == parent_id)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.order_by(Record.id.desc()).offset((page-1)*page_size).limit(page_size)
        rows = db.scalars(stmt).all()
        out = []
        for r in rows:
            data = json.loads(r.data_json)
            out.append({"id": r.id, "_parent_id": r.parent_id, **data})
        return out, total

def save_record(screen_slug: str, payload: Dict[str, Any], parent_id: Optional[int]=None, record_id: Optional[int]=None) -> int:
    schema = get_schema(screen_slug)
    data = merge_defaults(schema, payload)
    data = _server_recompute(schema, data)
    with SessionLocal() as db:
        if record_id:
            rec = db.get(Record, record_id)
            if not rec or rec.screen_slug != screen_slug:
                raise ValueError("Record not found")
            rec.data_json = json.dumps(data)
            if parent_id is not None:
                rec.parent_id = parent_id
            rec.schema_version = schema.get("version", rec.schema_version or 1)
            rec.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(rec)
            return rec.id
        rec = Record(screen_slug=screen_slug, parent_id=parent_id, data_json=json.dumps(data), schema_version=schema.get("version", 1))
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec.id


def update_record(screen_slug: str, record_id: int, payload: Dict[str, Any], parent_id: Optional[int] = None) -> int:
    schema = get_schema(screen_slug)
    data = merge_defaults(schema, payload)
    data = _server_recompute(schema, data)
    with SessionLocal() as db:
        rec = db.get(Record, record_id)
        if not rec or rec.screen_slug != screen_slug:
            raise ValueError("Record not found")
        rec.data_json = json.dumps(data)
        if parent_id is not None:
            rec.parent_id = parent_id
        rec.schema_version = schema.get("version", rec.schema_version or 1)
        rec.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(rec)
        return rec.id

def delete_record(record_id: int, screen_slug: Optional[str]=None) -> None:
    with SessionLocal() as db:
        rec = db.get(Record, record_id)
        if not rec or (screen_slug and rec.screen_slug != screen_slug):
            raise ValueError("Record not found")
        db.delete(rec)
        db.commit()

def get_record(rec_id: int, screen_slug: Optional[str]=None) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        r = db.get(Record, rec_id)
        if not r: return None
        if screen_slug and r.screen_slug != screen_slug:
            return None
        data = json.loads(r.data_json)
        data.setdefault("id", r.id)
        data.setdefault("_parent_id", r.parent_id)
        return data

def get_record_raw(rec_id: int, screen_slug: Optional[str]=None) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        rec = db.get(Record, rec_id)
        if not rec:
            return None
        if screen_slug and rec.screen_slug != screen_slug:
            return None
        payload = {
            "id": rec.id,
            "screen_slug": rec.screen_slug,
            "parent_id": rec.parent_id,
            "schema_version": rec.schema_version,
            "created_at": rec.created_at,
            "updated_at": rec.updated_at,
            "data_json": rec.data_json,
        }
        try:
            payload["data"] = json.loads(rec.data_json)
        except json.JSONDecodeError:
            payload["data"] = None
        return payload

def compute_rules(screen_slug: str, data_ctx: Dict[str, Any]) -> Dict[str, set]:
    schema = get_schema(screen_slug)
    return apply_rules(schema.get("rules", {}), data_ctx)


def _server_recompute(schema: dict, data: Dict[str, Any]) -> Dict[str, Any]:
    """Authoritative recompute of any fields that declare 'compute' (both top-level and group rows)."""
    # Top-level computed fields
    for f in schema.get("fields", []):
        if f.get("compute") and f.get("name"):
            # VERY constrained eval: arithmetic only, names from data
            try:
                expr = f["compute"]
                local_ctx = {k: data.get(k) for k in data.keys()}
                data[f["name"]] = eval(expr, {"__builtins__": {}}, local_ctx)
            except Exception:
                pass
        # Group rows
        if f.get("type") == "group" and f.get("mode") == "repeatable-table":
            rows = data.get(f["name"]) or []
            for row in rows:
                for sf in f.get("fields", []):
                    if sf.get("compute"):
                        try:
                            expr = sf["compute"]
                            local_ctx = {k: row.get(k) for k in row.keys()}
                            row[sf["name"]] = eval(expr, {"__builtins__": {}}, local_ctx)
                        except Exception:
                            pass
    return data
