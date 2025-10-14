from __future__ import annotations
import json
from typing import Any, Dict, Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from models import SessionLocal, Record, Schema
from schema_loader import get_schema
from rules import apply_rules

def _defaults_from_schema(schema: dict) -> Dict[str, Any]:
    d = {}
    for f in schema.get("fields", []):
        if f.get("default") is not None:
            d[f["name"]] = f["default"]
        else:
            d[f["name"]] = None
    return d

def merge_defaults(schema: dict, data: Dict[str, Any]) -> Dict[str, Any]:
    base = _defaults_from_schema(schema)
    base.update(data or {})
    return base

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
            out.append({"id": r.id, **data})
        return out, total

def save_record(screen_slug: str, payload: Dict[str, Any], parent_id: Optional[int]=None) -> int:
    schema = get_schema(screen_slug)
    data = merge_defaults(schema, payload)
    rec = Record(screen_slug=screen_slug, parent_id=parent_id, data_json=json.dumps(data), schema_version=schema.get("version", 1))
    with SessionLocal() as db:
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec.id

def get_record(rec_id: int) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        r = db.get(Record, rec_id)
        if not r: return None
        return json.loads(r.data_json)

def compute_rules(screen_slug: str, data_ctx: Dict[str, Any]) -> Dict[str, set]:
    schema = get_schema(screen_slug)
    return apply_rules(schema.get("rules", {}), data_ctx)
