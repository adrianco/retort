def test_update_book_returns_200_with_updated_fields(client):
    create_response = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert", "year": 1965}
    )
    book_id = create_response.json()["id"]

    response = client.put(
        f"/books/{book_id}",
        json={"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Dune Messiah"
    assert body["year"] == 1969


def test_update_book_missing_returns_404(client):
    response = client.put(
        "/books/999", json={"title": "Ghost", "author": "Nobody"}
    )

    assert response.status_code == 404


def test_update_book_missing_title_returns_422(client):
    create_response = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert"}
    )
    book_id = create_response.json()["id"]

    response = client.put(f"/books/{book_id}", json={"author": "Frank Herbert"})

    assert response.status_code == 422
