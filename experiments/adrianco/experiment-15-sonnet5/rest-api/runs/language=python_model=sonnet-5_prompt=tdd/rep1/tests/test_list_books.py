def test_list_books_returns_empty_list_when_none_exist(client):
    response = client.get("/books")

    assert response.status_code == 200
    assert response.json() == []


def test_list_books_returns_all_created_books(client):
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "Foundation", "author": "Isaac Asimov"})

    response = client.get("/books")

    assert response.status_code == 200
    titles = {book["title"] for book in response.json()}
    assert titles == {"Dune", "Foundation"}


def test_list_books_filters_by_author(client):
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "Foundation", "author": "Isaac Asimov"})

    response = client.get("/books", params={"author": "Frank Herbert"})

    assert response.status_code == 200
    books = response.json()
    assert len(books) == 1
    assert books[0]["title"] == "Dune"
