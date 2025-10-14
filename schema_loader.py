from __future__ import annotations
import json, os, copy
from typing import Dict, Any

SCREENS_DIR = os.environ.get("SCREENS_DIR", "forms")

_cache: Dict[str, Dict[str, Any]] = {}

def deep_merge(a: dict, b: dict) -> dict:
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out

def load_schema_from_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_extends(schema: dict, base_dir: str) -> dict:
    if "$extends" not in schema:
        return schema
    parent_path = os.path.join(base_dir, schema["$extends"])
    parent = load_schema_from_file(parent_path)
    parent = resolve_extends(parent, base_dir)
    merged = deep_merge(parent, {k: v for k, v in schema.items() if k != "$extends"})
    return merged

def load_schemas() -> Dict[str, dict]:
    global _cache
    m: Dict[str, dict] = {}
    for root, _, files in os.walk(SCREENS_DIR):
        for fn in files:
            if not fn.endswith(".json"): 
                continue
            p = os.path.join(root, fn)
            raw = load_schema_from_file(p)
            sch = resolve_extends(raw, root)
            slug = sch.get("slug") or os.path.splitext(fn)[0]
            sch["slug"] = slug
            m[slug] = sch
    _cache = m
    return m

def get_schema(slug: str) -> dict:
    if slug in _cache:
        return _cache[slug]
    load_schemas()
    return _cache.get(slug)
