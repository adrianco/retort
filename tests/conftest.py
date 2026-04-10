"""Shared test fixtures for retort tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from retort.design.factors import FactorRegistry, FactorType
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


@pytest.fixture
def two_level_registry() -> FactorRegistry:
    """Registry with 3 factors, each having 2 levels."""
    reg = FactorRegistry()
    reg.add("language", ["python", "go"])
    reg.add("agent", ["claude-code", "copilot"])
    reg.add("framework", ["fastapi", "stdlib"])
    return reg


@pytest.fixture
def mixed_level_registry() -> FactorRegistry:
    """Registry with factors having different numbers of levels."""
    reg = FactorRegistry()
    reg.add("language", ["python", "typescript", "rust", "go"])
    reg.add("agent", ["claude-code", "cursor", "copilot"])
    reg.add("framework", ["fastapi", "nextjs", "axum"])
    return reg


@pytest.fixture
def large_registry() -> FactorRegistry:
    """Registry with 6 factors (the full retort use case)."""
    reg = FactorRegistry()
    reg.add("language", ["python", "typescript", "rust", "go"])
    reg.add("agent", ["claude-code", "cursor", "copilot", "aider"])
    reg.add("framework", ["fastapi", "nextjs", "axum", "stdlib"])
    reg.add("app_type", ["rest-api", "cli-tool", "react-frontend"])
    reg.add("orchestration", ["single-agent", "swarm", "hive-mind"])
    reg.add("constraint_style", ["rfc-2119", "bdd", "unconstrained"])
    return reg
