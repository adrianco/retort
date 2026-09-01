BOOK = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


def test_health(client):
    assert client.request("GET", "/health") == (200, {"status": "ok"})


def test_create_and_get_book(client):
    status, body = client.request("POST", "/books", BOOK)
    assert status == 201
    assert body["id"] == 1
    assert {k: body[k] for k in BOOK} == BOOK
    assert client.request("GET", "/books/1") == (200, body)


def test_create_requires_title_and_author(client):
    status, body = client.request("POST", "/books", {"year": 2000})
    assert status == 422
    assert set(body["details"]) == {"title", "author"}
    status, _ = client.request("POST", "/books", {"title": "  ", "author": "X"})
    assert status == 422


def test_invalid_json_and_bad_year(client):
    import urllib.request
    req = urllib.request.Request(client.base + "/books", data=b"{not json",
                                 method="POST", headers={"Content-Type": "application/json"})
    import urllib.error
    try:
        urllib.request.urlopen(req)
        assert False, "expected 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400
    status, body = client.request("POST", "/books", {**BOOK, "year": "1965"})
    assert status == 422 and "year" in body["details"]


def test_list_and_author_filter(client):
    client.request("POST", "/books", BOOK)
    client.request("POST", "/books", {"title": "Emma", "author": "Jane Austen"})
    status, books = client.request("GET", "/books")
    assert status == 200 and [b["title"] for b in books] == ["Dune", "Emma"]
    status, books = client.request("GET", "/books?author=Jane%20Austen")
    assert status == 200 and [b["title"] for b in books] == ["Emma"]
    assert client.request("GET", "/books?author=Nobody") == (200, [])


def test_update_book(client):
    _, created = client.request("POST", "/books", BOOK)
    status, body = client.request("PUT", f"/books/{created['id']}",
                                  {"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})
    assert status == 200
    assert body["title"] == "Dune Messiah" and body["year"] == 1969 and body["isbn"] is None
    assert client.request("PUT", "/books/999", BOOK)[0] == 404
    assert client.request("PUT", "/books/1", {"title": "x"})[0] == 422


def test_delete_book(client):
    _, created = client.request("POST", "/books", BOOK)
    assert client.request("DELETE", f"/books/{created['id']}") == (204, None)
    assert client.request("GET", f"/books/{created['id']}")[0] == 404
    assert client.request("DELETE", f"/books/{created['id']}")[0] == 404


def test_unknown_routes(client):
    assert client.request("GET", "/nope")[0] == 404
    assert client.request("GET", "/books/abc")[0] == 404
    assert client.request("POST", "/health")[0] == 404
