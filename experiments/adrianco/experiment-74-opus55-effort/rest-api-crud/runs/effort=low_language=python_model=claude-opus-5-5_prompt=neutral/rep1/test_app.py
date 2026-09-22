import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / "test.db")).test_client()


def make(client, **kw):
    data = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}
    data.update(kw)
    return client.post("/books", json=data)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}


def test_create_and_get(client):
    r = make(client)
    assert r.status_code == 201
    book = r.get_json()
    assert book["id"] and book["title"] == "Dune"
    r = client.get(f"/books/{book['id']}")
    assert r.status_code == 200 and r.get_json() == book


@pytest.mark.parametrize("body", [{}, {"title": "X"}, {"author": "Y"}, {"title": " ", "author": "Y"},
                                  {"title": "X", "author": "Y", "year": "abc"}])
def test_validation(client, body):
    r = client.post("/books", json=body)
    assert r.status_code == 400 and "error" in r.get_json()


def test_invalid_json(client):
    r = client.post("/books", data="nope", content_type="application/json")
    assert r.status_code == 400


def test_list_with_author_filter(client):
    make(client)
    make(client, title="Emma", author="Jane Austen")
    assert len(client.get("/books").get_json()) == 2
    r = client.get("/books?author=jane austen").get_json()
    assert [b["title"] for b in r] == ["Emma"]


def test_update(client):
    bid = make(client).get_json()["id"]
    r = client.put(f"/books/{bid}", json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})
    assert r.status_code == 200 and r.get_json()["title"] == "Dune Messiah"
    assert client.put(f"/books/{bid}", json={"title": ""}).status_code == 400
    assert client.put("/books/999", json={"title": "a", "author": "b"}).status_code == 404


def test_delete(client):
    bid = make(client).get_json()["id"]
    assert client.delete(f"/books/{bid}").status_code == 204
    assert client.get(f"/books/{bid}").status_code == 404
    assert client.delete(f"/books/{bid}").status_code == 404
