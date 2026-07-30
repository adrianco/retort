import pytest

from app import create_app

SAMPLE = {
    "title": "The Left Hand of Darkness",
    "author": "Ursula K. Le Guin",
    "year": 1969,
    "isbn": "9780441478125",
}


@pytest.fixture
def client(tmp_path):
    app = create_app(database=str(tmp_path / "test.db"))
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = client.post("/books", json=SAMPLE)
    assert resp.status_code == 201
    body = resp.get_json()
    assert isinstance(body["id"], int)
    assert {k: body[k] for k in SAMPLE} == SAMPLE


def test_create_book_persists_and_is_listed(client):
    created = client.post("/books", json=SAMPLE).get_json()
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == [created]


def test_create_optional_fields_default_to_null(client):
    body = client.post("/books", json={"title": "Untitled", "author": "Anon"}).get_json()
    assert body["year"] is None and body["isbn"] is None


@pytest.mark.parametrize(
    "payload,field",
    [
        ({"author": "A"}, "title"),
        ({"title": "T"}, "author"),
        ({"title": "  ", "author": "A"}, "title"),
        ({"title": "T", "author": 5}, "author"),
        ({"title": "T", "author": "A", "year": "nineteen"}, "year"),
        ({"title": "T", "author": "A", "isbn": "123"}, "isbn"),
    ],
)
def test_create_validation_errors(client, payload, field):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    assert field in resp.get_json()["details"]


def test_create_without_body_is_400(client):
    assert client.post("/books").status_code == 400


def test_get_single_book(client):
    created = client.post("/books", json=SAMPLE).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_missing_book_is_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_list_filters_by_author(client):
    client.post("/books", json=SAMPLE)
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})

    resp = client.get("/books", query_string={"author": "Frank Herbert"})
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.get_json()]
    assert titles == ["Dune"]

    # Filter is case-insensitive, and unknown authors yield an empty list.
    assert len(client.get("/books", query_string={"author": "frank herbert"}).get_json()) == 1
    assert client.get("/books", query_string={"author": "Nobody"}).get_json() == []


def test_update_book(client):
    created = client.post("/books", json=SAMPLE).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "New Title", "author": "New Author", "year": 2001},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == created["id"]
    assert body["title"] == "New Title"
    assert body["author"] == "New Author"
    assert body["year"] == 2001
    assert body["isbn"] is None  # PUT replaces the whole resource
    assert client.get(f"/books/{created['id']}").get_json() == body


def test_update_validates_and_404s(client):
    created = client.post("/books", json=SAMPLE).get_json()
    assert client.put(f"/books/{created['id']}", json={"author": "A"}).status_code == 400
    assert client.put("/books/999", json=SAMPLE).status_code == 404


def test_delete_book(client):
    created = client.post("/books", json=SAMPLE).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert resp.get_data() == b""
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.delete(f"/books/{created['id']}").status_code == 404
    assert client.get("/books").get_json() == []


def test_data_survives_new_app_instance(tmp_path):
    path = str(tmp_path / "persist.db")
    with create_app(database=path).test_client() as c:
        book_id = c.post("/books", json=SAMPLE).get_json()["id"]
    with create_app(database=path).test_client() as c:
        assert c.get(f"/books/{book_id}").get_json()["title"] == SAMPLE["title"]


def test_unsupported_method_is_405(client):
    resp = client.delete("/books")
    assert resp.status_code == 405
    assert resp.get_json()["error"] == "method not allowed"
