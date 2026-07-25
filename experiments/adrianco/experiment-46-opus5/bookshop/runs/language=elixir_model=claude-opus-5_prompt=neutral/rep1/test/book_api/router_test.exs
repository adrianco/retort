defmodule BookApi.RouterTest do
  use BookApi.ApiCase

  describe "GET /health" do
    test "reports ok when the database is reachable" do
      conn = request(:get, "/health")

      assert conn.status == 200
      assert %{"status" => "ok", "service" => "book_api"} = json_body(conn)
    end
  end

  describe "POST /books" do
    test "creates a book and returns 201 with the persisted record" do
      conn =
        request(:post, "/books", %{
          title: "Designing Data-Intensive Applications",
          author: "Martin Kleppmann",
          year: 2017,
          isbn: "978-1449373320"
        })

      assert conn.status == 201
      body = json_body(conn)

      assert body["id"] > 0
      assert body["title"] == "Designing Data-Intensive Applications"
      assert body["author"] == "Martin Kleppmann"
      assert body["year"] == 2017
      assert body["isbn"] == "978-1449373320"

      assert Plug.Conn.get_resp_header(conn, "location") == ["/books/#{body["id"]}"]
      assert Repo.get(BookApi.Books.Book, body["id"])
    end

    test "creates a book when only the required fields are given" do
      conn = request(:post, "/books", %{title: "Untitled", author: "Anon"})

      assert conn.status == 201
      assert %{"year" => nil, "isbn" => nil} = json_body(conn)
    end

    test "returns 422 when title and author are missing" do
      conn = request(:post, "/books", %{year: 1999})

      assert conn.status == 422
      body = json_body(conn)

      assert body["error"] == "Validation failed"
      assert body["details"]["title"] == ["can't be blank"]
      assert body["details"]["author"] == ["can't be blank"]
    end

    test "returns 422 when title is blank after trimming" do
      conn = request(:post, "/books", %{title: "   ", author: "Anon"})

      assert conn.status == 422
      assert json_body(conn)["details"]["title"] == ["can't be blank"]
    end

    test "returns 422 for a malformed ISBN" do
      conn = request(:post, "/books", %{title: "T", author: "A", isbn: "not-an-isbn"})

      assert conn.status == 422
      assert json_body(conn)["details"]["isbn"] == ["must be a valid ISBN-10 or ISBN-13"]
    end

    test "returns 422 for a non-integer year" do
      conn = request(:post, "/books", %{title: "T", author: "A", year: "long ago"})

      assert conn.status == 422
      assert json_body(conn)["details"]["year"] == ["is invalid"]
    end

    test "ignores client-supplied ids" do
      conn = request(:post, "/books", %{id: 424_242, title: "T", author: "A"})

      assert conn.status == 201
      assert json_body(conn)["id"] != 424_242
    end

    test "returns 400 for a malformed JSON body" do
      conn = request(:post, "/books", ~s({"title": "T",))

      assert conn.status == 400
      assert json_body(conn)["error"] == "Malformed JSON body"
    end

    test "returns 415 for a non-JSON content type" do
      conn =
        :post
        |> Plug.Test.conn("/books", "title=T&author=A")
        |> Plug.Conn.put_req_header("content-type", "application/x-www-form-urlencoded")
        |> BookApi.Router.call(BookApi.Router.init([]))

      assert conn.status == 415
      assert json_body(conn)["error"] == "Content-Type must be application/json"
    end
  end

  describe "GET /books" do
    test "returns an empty list when there are no books" do
      conn = request(:get, "/books")

      assert conn.status == 200
      assert json_body(conn) == []
    end

    test "lists all books" do
      insert_book(%{"title" => "First", "author" => "Ada"})
      insert_book(%{"title" => "Second", "author" => "Grace"})

      conn = request(:get, "/books")

      assert conn.status == 200
      titles = conn |> json_body() |> Enum.map(& &1["title"])
      assert Enum.sort(titles) == ["First", "Second"]
    end

    test "filters by author, case-insensitively and on substrings" do
      insert_book(%{"title" => "First", "author" => "Ada Lovelace"})
      insert_book(%{"title" => "Second", "author" => "Grace Hopper"})

      conn = request(:get, "/books?author=lovelace")

      assert conn.status == 200
      assert [%{"title" => "First", "author" => "Ada Lovelace"}] = json_body(conn)
    end

    test "returns an empty list when the author filter matches nothing" do
      insert_book(%{"author" => "Ada Lovelace"})

      assert request(:get, "/books?author=nobody") |> json_body() == []
    end

    test "treats LIKE wildcards in the filter as literal characters" do
      insert_book(%{"title" => "Real", "author" => "Ada"})

      conn = request(:get, "/books?author=%25")

      assert conn.status == 200
      assert json_body(conn) == []
    end

    test "ignores a blank author filter" do
      insert_book(%{"author" => "Ada"})

      assert length(request(:get, "/books?author=") |> json_body()) == 1
    end
  end

  describe "GET /books/:id" do
    test "returns the requested book" do
      book = insert_book(%{"title" => "Findable", "author" => "Ada"})

      conn = request(:get, "/books/#{book.id}")

      assert conn.status == 200
      assert %{"id" => id, "title" => "Findable"} = json_body(conn)
      assert id == book.id
    end

    test "returns 404 for an unknown id" do
      conn = request(:get, "/books/999999")

      assert conn.status == 404
      assert json_body(conn)["error"] == "Book not found"
    end

    test "returns 404 for a non-numeric id" do
      conn = request(:get, "/books/abc")

      assert conn.status == 404
      assert json_body(conn)["error"] == "Book not found"
    end
  end

  describe "PUT /books/:id" do
    test "updates the given fields and persists them" do
      book = insert_book(%{"title" => "Old Title", "author" => "Ada", "year" => 1980})

      conn = request(:put, "/books/#{book.id}", %{title: "New Title", author: "Ada", year: 1985})

      assert conn.status == 200
      assert %{"title" => "New Title", "year" => 1985} = json_body(conn)

      reloaded = Repo.get!(BookApi.Books.Book, book.id)
      assert reloaded.title == "New Title"
      assert reloaded.year == 1985
    end

    test "applies a partial update, leaving omitted fields untouched" do
      book = insert_book(%{"title" => "Old Title", "author" => "Ada", "year" => 1980})

      conn = request(:put, "/books/#{book.id}", %{title: "New Title"})

      assert conn.status == 200
      assert %{"title" => "New Title", "author" => "Ada", "year" => 1980} = json_body(conn)
    end

    test "returns 422 when the update would blank a required field" do
      book = insert_book()

      conn = request(:put, "/books/#{book.id}", %{title: "", author: "Ada"})

      assert conn.status == 422
      assert json_body(conn)["details"]["title"] == ["can't be blank"]
      assert Repo.get!(BookApi.Books.Book, book.id).title == "A Title"
    end

    test "returns 404 for an unknown id" do
      conn = request(:put, "/books/999999", %{title: "T", author: "A"})

      assert conn.status == 404
    end
  end

  describe "DELETE /books/:id" do
    test "deletes the book and returns 204 with an empty body" do
      book = insert_book()

      conn = request(:delete, "/books/#{book.id}")

      assert conn.status == 204
      assert conn.resp_body == ""
      refute Repo.get(BookApi.Books.Book, book.id)
    end

    test "returns 404 when deleting twice" do
      book = insert_book()

      assert request(:delete, "/books/#{book.id}").status == 204
      assert request(:delete, "/books/#{book.id}").status == 404
    end
  end

  describe "unknown routes" do
    test "return 404 JSON" do
      conn = request(:get, "/nope")

      assert conn.status == 404
      assert json_body(conn)["error"] == "Not found"

      assert Plug.Conn.get_resp_header(conn, "content-type") == [
               "application/json; charset=utf-8"
             ]
    end
  end

  describe "full lifecycle" do
    test "create, read, list, update, delete" do
      created = request(:post, "/books", %{title: "Lifecycle", author: "Tester", year: 2024})
      assert created.status == 201
      id = json_body(created)["id"]

      assert request(:get, "/books/#{id}") |> json_body() |> Map.get("title") == "Lifecycle"
      assert length(request(:get, "/books") |> json_body()) == 1

      updated = request(:put, "/books/#{id}", %{title: "Lifecycle v2", author: "Tester"})
      assert updated.status == 200
      assert json_body(updated)["title"] == "Lifecycle v2"

      assert request(:delete, "/books/#{id}").status == 204
      assert request(:get, "/books/#{id}").status == 404
      assert request(:get, "/books") |> json_body() == []
    end
  end
end
