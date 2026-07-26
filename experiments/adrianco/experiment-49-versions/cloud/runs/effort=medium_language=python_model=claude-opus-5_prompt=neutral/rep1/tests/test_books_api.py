"""Integration tests driving the API through HTTP."""


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_book_returns_201_and_location(client, sample_book):
    resp = client.post("/books", json=sample_book)

    assert resp.status_code == 201
    body = resp.json()
    assert isinstance(body["id"], int)
    assert body["title"] == sample_book["title"]
    assert body["author"] == sample_book["author"]
    assert body["year"] == sample_book["year"]
    assert resp.headers["Location"] == f"/books/{body['id']}"


def test_create_book_persists_and_is_retrievable(client, sample_book):
    book_id = client.post("/books", json=sample_book).json()["id"]

    resp = client.get(f"/books/{book_id}")

    assert resp.status_code == 200
    assert resp.json() == {"id": book_id, **sample_book}


def test_create_book_accepts_minimal_payload(client):
    resp = client.post("/books", json={"title": "Untitled", "author": "Anon"})

    assert resp.status_code == 201
    assert resp.json()["year"] is None
    assert resp.json()["isbn"] is None


def test_list_books_returns_all_in_id_order(client, sample_book):
    client.post("/books", json=sample_book)
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})

    resp = client.get("/books")

    assert resp.status_code == 200
    titles = [b["title"] for b in resp.json()]
    assert titles == [sample_book["title"], "Dune"]


def test_list_books_is_empty_initially(client):
    assert client.get("/books").json() == []


def test_list_books_filters_by_author(client, sample_book):
    client.post("/books", json=sample_book)
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "Dune Messiah", "author": "Frank Herbert"})

    resp = client.get("/books", params={"author": "Frank Herbert"})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert {b["title"] for b in body} == {"Dune", "Dune Messiah"}


def test_list_books_filter_with_no_matches_returns_empty_list(client, sample_book):
    client.post("/books", json=sample_book)

    resp = client.get("/books", params={"author": "Nobody At All"})

    assert resp.status_code == 200
    assert resp.json() == []


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/9999")

    assert resp.status_code == 404
    assert "9999" in resp.json()["detail"]


def test_update_book_replaces_all_fields(client, sample_book):
    book_id = client.post("/books", json=sample_book).json()["id"]
    updated = {
        "title": "The Dispossessed",
        "author": "Ursula K. Le Guin",
        "year": 1974,
        "isbn": "978-0-06-051275-4",
    }

    resp = client.put(f"/books/{book_id}", json=updated)

    assert resp.status_code == 200
    assert resp.json() == {"id": book_id, **updated}
    assert client.get(f"/books/{book_id}").json() == {"id": book_id, **updated}


def test_update_clears_optional_fields_when_omitted(client, sample_book):
    book_id = client.post("/books", json=sample_book).json()["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "T", "author": "A"})

    assert resp.status_code == 200
    assert resp.json()["year"] is None
    assert resp.json()["isbn"] is None


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/4242", json={"title": "T", "author": "A"})

    assert resp.status_code == 404


def test_delete_book_returns_204_and_removes_it(client, sample_book):
    book_id = client.post("/books", json=sample_book).json()["id"]

    resp = client.delete(f"/books/{book_id}")

    assert resp.status_code == 204
    assert resp.content == b""
    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.get("/books").json() == []


def test_delete_missing_book_returns_404(client):
    assert client.delete("/books/1234").status_code == 404


def test_duplicate_isbn_returns_409(client, sample_book):
    client.post("/books", json=sample_book)

    resp = client.post("/books", json={**sample_book, "title": "Reprint"})

    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]
