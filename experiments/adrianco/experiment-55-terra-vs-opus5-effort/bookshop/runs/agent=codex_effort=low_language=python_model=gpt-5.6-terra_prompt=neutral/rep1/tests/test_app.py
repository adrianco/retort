import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    return app.test_client()


def make_book(client, **overrides):
    book = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    book.update(overrides)
    return client.post("/books", json=book)


def test_create_and_get_book(client):
    created = make_book(client)
    assert created.status_code == 201
    assert created.json["id"] == 1
    assert created.json["title"] == "Dune"

    fetched = client.get("/books/1")
    assert fetched.status_code == 200
    assert fetched.json == created.json


def test_list_can_filter_by_author(client):
    make_book(client, title="Dune")
    make_book(client, title="The Dispossessed", author="Ursula K. Le Guin")

    response = client.get("/books?author=Ursula%20K.%20Le%20Guin")
    assert response.status_code == 200
    assert [book["title"] for book in response.json] == ["The Dispossessed"]


def test_update_and_delete_book(client):
    make_book(client)
    updated = client.put("/books/1", json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})
    assert updated.status_code == 200
    assert updated.json["title"] == "Dune Messiah"
    assert updated.json["isbn"] is None

    deleted = client.delete("/books/1")
    assert deleted.status_code == 204
    assert client.get("/books/1").status_code == 404


def test_title_and_author_are_required(client):
    missing_title = client.post("/books", json={"author": "Octavia Butler"})
    blank_author = client.post("/books", json={"title": "Kindred", "author": " "})
    assert missing_title.status_code == 400
    assert blank_author.status_code == 400


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
