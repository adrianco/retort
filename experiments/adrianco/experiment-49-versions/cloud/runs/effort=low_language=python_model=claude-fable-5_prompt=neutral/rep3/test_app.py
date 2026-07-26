import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def make_book(client, **kwargs):
    data = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}
    data.update(kwargs)
    return client.post("/books", json=data)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = make_book(client)
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["title"] == "Dune"
    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Frank Herbert"


def test_create_validation(client):
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400
    assert "author is required" in resp.get_json()["errors"]
    resp = client.post("/books", json={"title": "", "author": "X"})
    assert resp.status_code == 400


def test_list_and_filter(client):
    make_book(client)
    make_book(client, title="Emma", author="Jane Austen", year=1815, isbn=None)
    assert len(client.get("/books").get_json()) == 2
    filtered = client.get("/books?author=Jane Austen").get_json()
    assert len(filtered) == 1
    assert filtered[0]["title"] == "Emma"


def test_update_book(client):
    book = make_book(client).get_json()
    resp = client.put(f"/books/{book['id']}", json={"year": 1966})
    assert resp.status_code == 200
    assert resp.get_json()["year"] == 1966
    assert resp.get_json()["title"] == "Dune"
    assert client.put("/books/999", json={"year": 1}).status_code == 404


def test_delete_book(client):
    book = make_book(client).get_json()
    assert client.delete(f"/books/{book['id']}").status_code == 204
    assert client.get(f"/books/{book['id']}").status_code == 404
    assert client.delete(f"/books/{book['id']}").status_code == 404
