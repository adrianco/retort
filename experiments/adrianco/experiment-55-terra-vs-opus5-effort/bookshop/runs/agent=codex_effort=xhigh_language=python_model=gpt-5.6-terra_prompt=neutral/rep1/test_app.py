"""Integration tests for the Book Collection API."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path: Path):
    app = create_app(tmp_path / "test-books.sqlite3")
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def create_book(client, **overrides):
    book = {
        "title": "Kindred",
        "author": "Octavia E. Butler",
        "year": 1979,
        "isbn": "9780807083697",
    }
    book.update(overrides)
    return client.post("/books", json=book)


def test_create_and_get_a_book(client):
    created = create_book(client)

    assert created.status_code == 201
    saved = created.get_json()
    assert saved == {
        "id": 1,
        "title": "Kindred",
        "author": "Octavia E. Butler",
        "year": 1979,
        "isbn": "9780807083697",
    }

    fetched = client.get("/books/1")
    assert fetched.status_code == 200
    assert fetched.get_json() == saved


def test_list_books_can_filter_by_author(client):
    create_book(client, title="Kindred")
    create_book(client, title="Parable of the Sower")
    create_book(client, title="A Wizard of Earthsea", author="Ursula K. Le Guin")

    response = client.get("/books?author=octavia%20e.%20butler")

    assert response.status_code == 200
    assert [book["title"] for book in response.get_json()] == [
        "Kindred",
        "Parable of the Sower",
    ]


def test_update_then_delete_a_book(client):
    create_book(client)

    updated = client.put(
        "/books/1",
        json={"title": "Fledgling", "author": "Octavia E. Butler", "year": 2005},
    )
    assert updated.status_code == 200
    assert updated.get_json()["title"] == "Fledgling"
    assert updated.get_json()["isbn"] is None

    deleted = client.delete("/books/1")
    assert deleted.status_code == 204
    assert deleted.data == b""
    assert client.get("/books/1").status_code == 404


def test_title_and_author_are_required(client):
    response = client.post("/books", json={"title": ""})

    assert response.status_code == 400
    assert "author" in response.get_json()["error"] or "title" in response.get_json()["error"]


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
