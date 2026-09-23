import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / "test.db")).test_client()


def make(client, **kw):
    data = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593", **kw}
    return client.post("/books", json=data)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}


def test_create_and_get(client):
    r = make(client)
    assert r.status_code == 201
    book = r.get_json()
    assert book["id"] and book["title"] == "Dune"
    assert client.get(f"/books/{book['id']}").get_json() == book


@pytest.mark.parametrize("body", [{"author": "X"}, {"title": "X"}, {"title": " ", "author": "X"},
                                  {"title": "X", "author": "Y", "year": "abc"}, None])
def test_validation(client, body):
    r = client.post("/books", json=body) if body is not None else client.post("/books", data="nope")
    assert r.status_code == 400 and "error" in r.get_json()


def test_list_with_author_filter(client):
    make(client)
    make(client, title="Emma", author="Jane Austen")
    assert len(client.get("/books").get_json()) == 2
    res = client.get("/books?author=Jane Austen").get_json()
    assert [b["title"] for b in res] == ["Emma"]


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
