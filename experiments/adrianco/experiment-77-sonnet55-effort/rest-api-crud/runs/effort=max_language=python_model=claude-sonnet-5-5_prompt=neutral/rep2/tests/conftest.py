"""Shared fixtures: a fresh in-memory repository, app and in-process client per test."""

from __future__ import annotations

import pytest
from support import WSGIClient

from bookapi.app import BookApp
from bookapi.repository import BookRepository


@pytest.fixture
def repository():
    repo = BookRepository(":memory:")
    yield repo
    repo.close()


@pytest.fixture
def app(repository):
    return BookApp(repository)


@pytest.fixture
def client(app):
    return WSGIClient(app)
