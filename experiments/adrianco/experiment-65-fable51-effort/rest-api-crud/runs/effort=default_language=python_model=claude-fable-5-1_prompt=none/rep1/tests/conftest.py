import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def book(client):
    """A pre-created book, returned as the response JSON."""
    resp = client.post("/books", json={
        "title": "Dune", "author": "Frank Herbert", "year": 1965,
        "isbn": "978-0441013593",
    })
    assert resp.status_code == 201
    return resp.get_json()
