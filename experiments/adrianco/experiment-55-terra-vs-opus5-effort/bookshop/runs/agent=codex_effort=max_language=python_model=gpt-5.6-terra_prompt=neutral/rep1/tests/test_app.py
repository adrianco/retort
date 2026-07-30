from __future__ import annotations

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "books-test.sqlite3"),
        }
    )
    with app.test_client() as test_client:
        yield test_client


def make_book(client, **overrides):
    book = {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "year": 1969,
        "isbn": "978-0441478125",
    }
    book.update(overrides)
    return client.post("/books", json=book)


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_list_and_filter_books_by_author(client):
    first = make_book(client)
    second = make_book(
        client,
        title="A Wizard of Earthsea",
        year=1968,
        isbn="978-0547773742",
    )
    make_book(client, title="Kindred", author="Octavia E. Butler", year=1979)

    assert first.status_code == 201
    assert first.get_json()["id"] == 1
    assert second.status_code == 201

    all_books = client.get("/books")
    assert all_books.status_code == 200
    assert [book["title"] for book in all_books.get_json()] == [
        "The Left Hand of Darkness",
        "A Wizard of Earthsea",
        "Kindred",
    ]

    filtered = client.get("/books?author=Ursula%20K.%20Le%20Guin")
    assert filtered.status_code == 200
    assert [book["title"] for book in filtered.get_json()] == [
        "The Left Hand of Darkness",
        "A Wizard of Earthsea",
    ]


def test_get_update_and_delete_book(client):
    created = make_book(client).get_json()

    fetched = client.get(f"/books/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.get_json()["title"] == "The Left Hand of Darkness"

    updated = client.put(
        f"/books/{created['id']}",
        json={
            "title": "The Dispossessed",
            "author": "Ursula K. Le Guin",
            "year": 1974,
            "isbn": "978-0061054884",
        },
    )
    assert updated.status_code == 200
    assert updated.get_json() == {
        "id": created["id"],
        "title": "The Dispossessed",
        "author": "Ursula K. Le Guin",
        "year": 1974,
        "isbn": "978-0061054884",
    }

    deleted = client.delete(f"/books/{created['id']}")
    assert deleted.status_code == 204
    assert deleted.data == b""
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_required_fields_and_invalid_values_are_rejected(client):
    missing_title = client.post("/books", json={"author": "Toni Morrison"})
    bad_year = client.post(
        "/books",
        json={"title": "Beloved", "author": "Toni Morrison", "year": "1987"},
    )

    assert missing_title.status_code == 400
    assert "title" in missing_title.get_json()["details"]
    assert bad_year.status_code == 400
    assert "year" in bad_year.get_json()["details"]
