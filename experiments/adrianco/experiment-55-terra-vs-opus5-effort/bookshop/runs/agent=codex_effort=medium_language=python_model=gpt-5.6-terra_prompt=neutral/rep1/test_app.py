import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(str(tmp_path / "books.db"))
    app.config["TESTING"] = True
    return app.test_client()


def create(client, **overrides):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_create_and_get_book(client):
    response = create(client)
    assert response.status_code == 201
    book = response.get_json()
    assert book == {"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}

    response = client.get("/books/1")
    assert response.status_code == 200
    assert response.get_json() == book


def test_list_filter_update_and_delete(client):
    create(client)
    create(client, title="Kindred", author="Octavia Butler", year=1979)

    filtered = client.get("/books?author=Frank%20Herbert")
    assert [book["title"] for book in filtered.get_json()] == ["Dune"]

    updated = client.put("/books/1", json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})
    assert updated.status_code == 200
    assert updated.get_json()["title"] == "Dune Messiah"
    assert updated.get_json()["isbn"] is None

    assert client.delete("/books/1").status_code == 204
    assert client.get("/books/1").status_code == 404


def test_validation_health_and_missing_book(client):
    assert client.get("/health").get_json() == {"status": "ok"}
    response = client.post("/books", json={"title": "Only a title"})
    assert response.status_code == 400
    assert "author" in response.get_json()["error"]
    assert client.put("/books/99", json={"title": "x", "author": "y"}).status_code == 404
