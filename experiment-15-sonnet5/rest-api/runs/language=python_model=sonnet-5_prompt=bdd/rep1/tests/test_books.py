def _create_book(client, **overrides):
    payload = {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "isbn": "9780441013593",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_given_valid_book_data_when_creating_book_then_book_is_persisted_with_id(client):
    # Given valid book data
    # When a new book is created
    response = _create_book(client)

    # Then the book is returned with a generated id and the submitted fields
    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441013593"


def test_given_missing_title_when_creating_book_then_returns_422(client):
    # Given book data with no title
    # When the book is created
    response = _create_book(client, title="")

    # Then the request is rejected as invalid
    assert response.status_code == 422


def test_given_missing_author_when_creating_book_then_returns_422(client):
    # Given book data with no author
    payload = {"title": "Dune", "year": 1965, "isbn": "9780441013593"}

    # When the book is created without an author field
    response = client.post("/books", json=payload)

    # Then the request is rejected as invalid
    assert response.status_code == 422


def test_given_existing_books_when_listing_books_then_all_books_are_returned(client):
    # Given two existing books
    _create_book(client, title="Dune")
    _create_book(client, title="Children of Dune", author="Frank Herbert")

    # When listing all books
    response = client.get("/books")

    # Then both books are present in the response
    assert response.status_code == 200
    titles = [book["title"] for book in response.json()]
    assert titles == ["Dune", "Children of Dune"]


def test_given_books_by_different_authors_when_filtering_by_author_then_only_matching_books_are_returned(client):
    # Given books by two different authors
    _create_book(client, title="Dune", author="Frank Herbert")
    _create_book(client, title="Foundation", author="Isaac Asimov")

    # When listing books filtered by author
    response = client.get("/books", params={"author": "Asimov"})

    # Then only the matching author's book is returned
    assert response.status_code == 200
    books = response.json()
    assert len(books) == 1
    assert books[0]["title"] == "Foundation"


def test_given_existing_book_when_fetching_by_id_then_matching_book_is_returned(client):
    # Given an existing book
    created = _create_book(client).json()

    # When fetching that book by its id
    response = client.get(f"/books/{created['id']}")

    # Then the matching book is returned
    assert response.status_code == 200
    assert response.json() == created


def test_given_no_book_with_id_when_fetching_by_id_then_returns_404(client):
    # Given no book exists with a particular id
    # When fetching that id
    response = client.get("/books/999")

    # Then a not found response is returned
    assert response.status_code == 404


def test_given_existing_book_when_updating_book_then_fields_are_replaced(client):
    # Given an existing book
    created = _create_book(client).json()

    # When updating the book with new field values
    response = client.put(
        f"/books/{created['id']}",
        json={
            "title": "Dune Messiah",
            "author": "Frank Herbert",
            "year": 1969,
            "isbn": "9780441172696",
        },
    )

    # Then the book reflects the updated values
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Dune Messiah"
    assert body["year"] == 1969


def test_given_no_book_with_id_when_updating_book_then_returns_404(client):
    # Given no book exists with a particular id
    # When attempting to update that id
    response = client.put(
        "/books/999",
        json={"title": "Ghost", "author": "Nobody"},
    )

    # Then a not found response is returned
    assert response.status_code == 404


def test_given_existing_book_when_deleting_book_then_book_is_removed(client):
    # Given an existing book
    created = _create_book(client).json()

    # When deleting the book
    delete_response = client.delete(f"/books/{created['id']}")

    # Then the deletion succeeds and the book can no longer be fetched
    assert delete_response.status_code == 204
    get_response = client.get(f"/books/{created['id']}")
    assert get_response.status_code == 404


def test_given_no_book_with_id_when_deleting_book_then_returns_404(client):
    # Given no book exists with a particular id
    # When attempting to delete that id
    response = client.delete("/books/999")

    # Then a not found response is returned
    assert response.status_code == 404
