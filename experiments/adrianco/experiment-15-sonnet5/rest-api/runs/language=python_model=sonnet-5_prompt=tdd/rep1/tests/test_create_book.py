def test_create_book_returns_201_with_created_book(client):
    payload = {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "9780441013593",
    }

    response = client.post("/books", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441013593"
    assert "id" in body


def test_create_book_missing_title_returns_422(client):
    payload = {"author": "Frank Herbert", "year": 1965, "isbn": "123"}

    response = client.post("/books", json=payload)

    assert response.status_code == 422


def test_create_book_missing_author_returns_422(client):
    payload = {"title": "Dune", "year": 1965, "isbn": "123"}

    response = client.post("/books", json=payload)

    assert response.status_code == 422
