import pytest

from bookapi import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "books.db")})


@pytest.fixture
def client(app):
    return app.test_client()
