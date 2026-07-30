from __future__ import annotations

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    application = create_app(
        {"TESTING": True, "DATABASE": str(tmp_path / "test-books.sqlite3")}
    )
    with application.test_client() as test_client:
        yield test_client


def create_book(client, **overrides):
    payload = {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "year": 1969,
        "isbn": "978-0441478125",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_read_update_and_delete_book(client):
    created = create_book(client)

    assert created.status_code == 201
    book = created.get_json()
    assert book == {
        "id": 1,
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "year": 1969,
        "isbn": "978-0441478125",
    }

    fetched = client.get("/books/1")
    assert fetched.status_code == 200
    assert fetched.get_json() == book

    updated = client.put(
        "/books/1",
        json={
            "title": "The Dispossessed",
            "author": "Ursula K. Le Guin",
            "year": 1974,
            "isbn": "978-0061054884",
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()["title"] == "The Dispossessed"
    assert updated.get_json()["year"] == 1974

    deleted = client.delete("/books/1")
    assert deleted.status_code == 204
    assert deleted.data == b""

    missing = client.get("/books/1")
    assert missing.status_code == 404
    assert missing.get_json() == {"error": "Book not found"}


def test_list_books_can_filter_by_author(client):
    create_book(client, title="A Wizard of Earthsea", year=1968)
    create_book(
        client,
        title="Kindred",
        author="Octavia E. Butler",
        year=1979,
        isbn="978-0807083697",
    )
    create_book(client, title="The Tombs of Atuan", year=1971)

    all_books = client.get("/books")
    assert all_books.status_code == 200
    assert [book["id"] for book in all_books.get_json()] == [1, 2, 3]

    filtered = client.get("/books?author=ursula%20k.%20le%20guin")
    assert filtered.status_code == 200
    assert [book["title"] for book in filtered.get_json()] == [
        "A Wizard of Earthsea",
        "The Tombs of Atuan",
    ]


@pytest.mark.parametrize(
    "payload, expected_error",
    [
        ({"author": "Octavia E. Butler"}, "title is required"),
        ({"title": "Kindred"}, "author is required"),
        ({"title": "Kindred", "author": "Octavia E. Butler", "year": "1979"}, "year must be an integer"),
    ],
)
def test_book_payload_validation(client, payload, expected_error):
    response = client.post("/books", json=payload)

    assert response.status_code == 400
    assert expected_error in response.get_json()["error"]


def test_updating_or_deleting_unknown_book_returns_json_404(client):
    updated = client.put(
        "/books/999",
        json={"title": "Kindred", "author": "Octavia E. Butler"},
    )
    deleted = client.delete("/books/999")

    assert updated.status_code == 404
    assert updated.get_json() == {"error": "Book not found"}
    assert deleted.status_code == 404
    assert deleted.get_json() == {"error": "Book not found"}
