import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / "t.db")).test_client()


def mk(client, **kw):
    body = {"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"}
    body.update(kw)
    return client.post("/books", json=body)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json["status"] == "ok"


def test_create_and_get(client):
    r = mk(client)
    assert r.status_code == 201
    assert r.json["id"] == 1 and r.json["title"] == "Dune"
    assert client.get("/books/1").json["author"] == "Herbert"


def test_validation(client):
    assert client.post("/books", json={"author": "x"}).status_code == 400
    assert client.post("/books", json={"title": "x", "author": " "}).status_code == 400
    assert mk(client, year="abc").status_code == 400
    assert client.post("/books", data="junk").status_code == 400


def test_list_and_filter(client):
    mk(client)
    mk(client, title="Emma", author="Austen")
    assert len(client.get("/books").json) == 2
    r = client.get("/books?author=Austen")
    assert [b["title"] for b in r.json] == ["Emma"]


def test_update(client):
    mk(client)
    r = client.put("/books/1", json={"title": "New", "author": "Herbert"})
    assert r.status_code == 200 and r.json["title"] == "New"
    assert client.put("/books/1", json={"title": ""}).status_code == 400
    assert client.put("/books/99", json={"title": "a", "author": "b"}).status_code == 404


def test_delete(client):
    mk(client)
    assert client.delete("/books/1").status_code == 204
    assert client.get("/books/1").status_code == 404
    assert client.delete("/books/1").status_code == 404
