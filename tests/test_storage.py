from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
import storage
from schema_loader import load_schemas
from storage import save_record, list_records, delete_record


@pytest.fixture(autouse=True)
def fresh_database(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", echo=False, future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    monkeypatch.setattr(models, "engine", engine, raising=False)
    monkeypatch.setattr(models, "SessionLocal", TestingSessionLocal, raising=False)
    monkeypatch.setattr(storage, "SessionLocal", TestingSessionLocal, raising=False)
    monkeypatch.setattr(models, "_db_initialized", False, raising=False)

    models.Base.metadata.create_all(bind=engine)
    load_schemas()
    yield
    engine.dispose()


def test_save_record_updates_existing():
    payload = {'date': '2024-01-01', 'work_done': 'Initial', 'cost': 10}
    rec_id = save_record('service_table', payload)
    assert rec_id is not None

    updated_payload = {'date': '2024-01-02', 'work_done': 'Updated', 'cost': 25}
    updated_id = save_record('service_table', updated_payload, record_id=rec_id)
    assert updated_id == rec_id

    rows, total = list_records('service_table')
    assert total == 1
    assert rows[0]['cost'] == 25
    assert rows[0]['date'] == '2024-01-02'


def test_delete_record_removes_entry():
    payload = {'date': '2024-03-01', 'work_done': 'To be deleted', 'cost': 5}
    rec_id = save_record('service_table', payload)
    rows, total = list_records('service_table')
    assert total == 1

    delete_record(rec_id, screen_slug='service_table')
    rows, total = list_records('service_table')
    assert total == 0
    assert rows == []

    with pytest.raises(ValueError):
        delete_record(rec_id, screen_slug='service_table')


def test_recompute_preview_calculates_fields(monkeypatch):
    schema = {
        'fields': [
            {'name': 'base', 'type': 'number'},
            {'name': 'computed', 'type': 'number', 'compute': 'base * 2'},
            {
                'name': 'items',
                'type': 'group',
                'mode': 'repeatable-table',
                'fields': [
                    {'name': 'qty', 'type': 'number'},
                    {'name': 'price', 'type': 'number'},
                    {'name': 'line_total', 'type': 'number', 'compute': 'qty * price'},
                ],
            },
        ]
    }

    monkeypatch.setattr(storage, 'get_schema', lambda slug: schema)

    payload = {
        'base': 3,
        'items': [
            {'qty': 2, 'price': 5},
            {'qty': 1, 'price': 4},
        ],
    }

    result = storage.recompute_preview('dummy', payload)

    assert result['computed'] == 6
    assert result['items'][0]['line_total'] == 10
    assert result['items'][1]['line_total'] == 4
