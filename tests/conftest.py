"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from retort.storage.models import Base


@pytest.fixture
def db_engine(tmp_path: Path):
    """Create a fresh in-memory SQLite engine with all tables."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    """Provide a transactional session that rolls back after each test."""
    factory = sessionmaker(bind=db_engine)
    session = factory()
    yield session
    session.close()
