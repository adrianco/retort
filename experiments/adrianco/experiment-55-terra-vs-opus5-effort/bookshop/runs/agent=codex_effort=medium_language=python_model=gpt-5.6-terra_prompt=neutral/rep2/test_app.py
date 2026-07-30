import sqlite3

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "books.sqlite")})
    return app.test_client()


def create(client, **overrides):
    book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    book.update(overrides)
    return client.post("/books", json=book)


def test_create_and_get_book(client):
    response = create(client)
    assert response.status_code == 201
    assert response.json["id"] == 1
    assert response.json["title"] == "Dune"

    response = client.get("/books/1")
    assert response.status_code == 200
    assert response.json["author"] == "Frank Herbert"


def test_list_filter_update_and_delete(client):
    create(client)
    create(client, title="The Left Hand of Darkness", author="Ursula K. Le Guin")

    response = client.get("/books?author=frank%20herbert")
    assert response.status_code == 200
    assert [book["title"] for book in response.json] == ["Dune"]

    response = client.put("/books/1", json={"title": "Dune Messiah"})
    assert response.status_code == 200
    assert response.json["title"] == "Dune Messiah"
    assert response.json["author"] == "Frank Herbert"

    response = client.delete("/books/1")
    assert response.status_code == 204
    assert client.get("/books/1").status_code == 404


def test_validation_and_health(client):
    response = client.post("/books", json={"title": ""})
    assert response.status_code == 400
    assert "title" in response.json["error"]

    response = client.post("/books", json={"title": "Valid", "author": "Writer", "year": "2020"})
    assert response.status_code == 400
    assert "year" in response.json["error"]

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
