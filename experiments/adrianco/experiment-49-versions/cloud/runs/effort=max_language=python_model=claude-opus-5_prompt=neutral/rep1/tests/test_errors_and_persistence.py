"""Tests for API-wide error handling, routing quirks and durability."""

from bookapi import create_app
from sample_data import SAMPLE_BOOK


def test_unknown_route_returns_json_404(client):
    response = client.get("/not-a-real-route")

    assert response.status_code == 404
    assert response.headers["Content-Type"].startswith("application/json")
    assert "error" in response.get_json()


def test_wrong_method_returns_json_405(client, make_book):
    created = make_book()

    response = client.post(f"/books/{created['id']}", json={})

    assert response.status_code == 405
    assert "error" in response.get_json()
    assert "Allow" in response.headers


def test_trailing_slash_is_accepted(client, make_book):
    make_book()

    assert client.get("/books/").status_code == 200


def test_missing_content_type_header_is_tolerated(client):
    response = client.post(
        "/books", data='{"title": "Dune", "author": "Frank Herbert"}'
    )

    assert response.status_code == 201


def test_data_survives_a_restart(db_path):
    """A second app instance sees rows written by the first one."""
    first = create_app({"TESTING": True, "DATABASE": db_path})
    created = first.test_client().post("/books", json=SAMPLE_BOOK).get_json()

    second = create_app({"TESTING": True, "DATABASE": db_path})
    response = second.test_client().get(f"/books/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == created


def test_apps_with_different_databases_are_isolated(db_path, tmp_path):
    create_app({"TESTING": True, "DATABASE": db_path}).test_client().post(
        "/books", json=SAMPLE_BOOK
    )

    other = create_app({"TESTING": True, "DATABASE": str(tmp_path / "other.db")})

    assert other.test_client().get("/books").get_json() == []
