from __future__ import annotations
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, sessionmaker

DATABASE_URL = "sqlite:///app.db"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

_db_initialized = False

class Schema(Base):
    __tablename__ = "schemas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), index=True, unique=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    json: Mapped[str] = mapped_column(Text)  # raw JSON text for the screen

class Record(Base):
    __tablename__ = "records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    screen_slug: Mapped[str] = mapped_column(String(100), index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    data_json: Mapped[str] = mapped_column(Text)  # raw JSON of the record
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

def init_db():
    global _db_initialized
    if _db_initialized:
        return
    Base.metadata.create_all(bind=engine)
    _db_initialized = True
