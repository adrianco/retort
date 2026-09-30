import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / "t.db")).test_client()


def make(client, **kw):
    body = {"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"}
    body.update(kw)
    return client.post("/books", json=body)


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_create_and_get(client):
    r = make(client)
    assert r.status_code == 201
    book = r.get_json()
    assert client.get(f"/books/{book['id']}").get_json() == book


def test_validation(client):
    assert make(client, title="").status_code == 400
    assert client.post("/books", json={"title": "x"}).status_code == 400
    assert make(client, year="abc").status_code == 400


def test_list_filter(client):
    make(client)
    make(client, author="Asimov")
    assert len(client.get("/books").get_json()) == 2
    res = client.get("/books?author=Asimov").get_json()
    assert [b["author"] for b in res] == ["Asimov"]


def test_update_and_delete(client):
    bid = make(client).get_json()["id"]
    r = client.put(f"/books/{bid}", json={"title": "New", "author": "A"})
    assert r.status_code == 200 and r.get_json()["title"] == "New"
    assert client.put(f"/books/{bid}", json={"title": "x"}).status_code == 400
    assert client.delete(f"/books/{bid}").status_code == 204
    assert client.get(f"/books/{bid}").status_code == 404
    assert client.delete(f"/books/{bid}").status_code == 404
    assert client.put("/books/99", json={"title": "a", "author": "b"}).status_code == 404
