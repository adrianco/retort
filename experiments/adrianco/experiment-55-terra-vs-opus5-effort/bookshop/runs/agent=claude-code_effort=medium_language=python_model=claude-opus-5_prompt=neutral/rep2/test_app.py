import pytest

from app import create_app

BOOK = {
    "title": "The Left Hand of Darkness",
    "author": "Ursula K. Le Guin",
    "year": 1969,
    "isbn": "9780441478125",
}


@pytest.fixture
def client(tmp_path):
    app = create_app(database=str(tmp_path / "test.db"))
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def post(client, **overrides):
    payload = {**BOOK, **overrides}
    return client.post("/books", json=payload)


def test_health_reports_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "database": "ok"}


def test_health_reports_503_when_database_is_unreadable(tmp_path):
    database = tmp_path / "corrupt.db"
    app = create_app(database=str(database))
    with app.test_client() as client:
        assert client.get("/health").status_code == 200
        database.write_bytes(b"not a sqlite database" * 100)
        resp = client.get("/health")
    assert resp.status_code == 503
    assert resp.get_json() == {"status": "error", "database": "unavailable"}


def test_create_book_returns_201_with_id_and_location(client):
    resp = post(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert isinstance(body["id"], int)
    assert {k: body[k] for k in BOOK} == BOOK
    assert resp.headers["Location"] == f"/books/{body['id']}"


def test_create_book_persists_and_is_retrievable(client):
    created = post(client).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_optional_fields_default_to_null(client):
    body = client.post(
        "/books", json={"title": "Untitled", "author": "Anon"}
    ).get_json()
    assert body["year"] is None
    assert body["isbn"] is None


@pytest.mark.parametrize(
    "payload,missing",
    [
        ({"author": "Anon"}, "title is required"),
        ({"title": "Untitled"}, "author is required"),
        ({}, "title is required"),
        ({"title": "   ", "author": "Anon"}, "title must not be empty"),
        ({"title": 42, "author": "Anon"}, "title must be a string"),
    ],
)
def test_create_rejects_invalid_payloads(client, payload, missing):
    resp = client.post("/books", json=payload)
    assert resp.status_code == 400
    assert missing in resp.get_json()["details"]


def test_create_rejects_bad_year(client):
    resp = post(client, year="nineteen sixty-nine")
    assert resp.status_code == 400
    assert resp.get_json()["details"] == ["year must be an integer"]

    resp = post(client, year=9999)
    assert resp.status_code == 400
    assert "year must be between" in resp.get_json()["details"][0]


def test_create_rejects_non_object_and_malformed_json(client):
    assert client.post("/books", json=["not", "an", "object"]).status_code == 400
    assert client.post(
        "/books", data="{oops", content_type="application/json"
    ).status_code == 400


def test_list_books_returns_all_in_id_order(client):
    assert client.get("/books").get_json() == []
    first = post(client).get_json()
    second = post(client, title="The Dispossessed").get_json()

    resp = client.get("/books")
    assert resp.status_code == 200
    assert [b["id"] for b in resp.get_json()] == [first["id"], second["id"]]


def test_list_books_filters_by_author(client):
    post(client)
    post(client, title="Kindred", author="Octavia E. Butler")

    resp = client.get("/books", query_string={"author": "Octavia E. Butler"})
    assert resp.status_code == 200
    assert [b["title"] for b in resp.get_json()] == ["Kindred"]

    # Filtering is case-insensitive and ignores surrounding whitespace.
    assert len(client.get("/books?author=octavia+e.+butler").get_json()) == 1
    assert len(client.get("/books?author=%20Octavia%20E.%20Butler%20").get_json()) == 1
    assert client.get("/books?author=Nobody").get_json() == []


def test_update_replaces_all_fields(client):
    created = post(client).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "The Dispossessed", "author": "U. Le Guin", "year": 1974},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {
        "id": created["id"],
        "title": "The Dispossessed",
        "author": "U. Le Guin",
        "year": 1974,
        "isbn": None,  # omitted on update, so it is cleared
    }
    assert client.get(f"/books/{created['id']}").get_json() == resp.get_json()


def test_update_validates_payload(client):
    created = post(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": "No Author"})
    assert resp.status_code == 400
    # The stored record is untouched.
    assert client.get(f"/books/{created['id']}").get_json() == created


def test_delete_removes_book(client):
    created = post(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert resp.data == b""
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.get("/books").get_json() == []


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_book_returns_404_json(client, method):
    kwargs = {"json": BOOK} if method == "put" else {}
    resp = getattr(client, method)("/books/9999", **kwargs)
    assert resp.status_code == 404
    assert resp.is_json
    assert resp.get_json()["error"] == "Not Found"


def test_non_integer_id_returns_404_json(client):
    resp = client.get("/books/abc")
    assert resp.status_code == 404
    assert resp.is_json


def test_data_survives_a_new_app_instance(tmp_path):
    database = str(tmp_path / "persist.db")
    with create_app(database=database).test_client() as client:
        created = post(client).get_json()

    with create_app(database=database).test_client() as client:
        assert client.get(f"/books/{created['id']}").get_json() == created
