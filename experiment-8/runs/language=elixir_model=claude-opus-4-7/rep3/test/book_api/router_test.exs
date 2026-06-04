defmodule BookApi.RouterTest do
  use BookApi.ConnCase, async: false

  describe "GET /health" do
    test "returns ok" do
      conn = call(:get, "/health")
      assert conn.status == 200
      assert json_body(conn) == %{"status" => "ok"}
    end
  end

  describe "POST /books" do
    test "creates a book with valid params" do
      conn =
        call(:post, "/books", %{
          title: "Programming Elixir",
          author: "Dave Thomas",
          year: 2018,
          isbn: "978-1680502992"
        })

      assert conn.status == 201
      body = json_body(conn)
      assert body["id"]
      assert body["title"] == "Programming Elixir"
      assert body["author"] == "Dave Thomas"
      assert body["year"] == 2018
      assert body["isbn"] == "978-1680502992"
    end

    test "rejects missing required fields" do
      conn = call(:post, "/books", %{year: 2020})
      assert conn.status == 422
      body = json_body(conn)
      assert body["errors"]["title"]
      assert body["errors"]["author"]
    end

    test "rejects blank title" do
      conn = call(:post, "/books", %{title: "", author: "Someone"})
      assert conn.status == 422
      assert json_body(conn)["errors"]["title"]
    end
  end

  describe "GET /books" do
    test "lists all books" do
      {:ok, _} =
        BookApi.Books.create_book(%{title: "Book A", author: "Alice"})

      {:ok, _} =
        BookApi.Books.create_book(%{title: "Book B", author: "Bob"})

      conn = call(:get, "/books")
      assert conn.status == 200
      body = json_body(conn)
      assert length(body) == 2
    end

    test "filters by author" do
      {:ok, _} = BookApi.Books.create_book(%{title: "A1", author: "Alice"})
      {:ok, _} = BookApi.Books.create_book(%{title: "A2", author: "Alice"})
      {:ok, _} = BookApi.Books.create_book(%{title: "B1", author: "Bob"})

      conn = call(:get, "/books?author=Alice")
      assert conn.status == 200
      body = json_body(conn)
      assert length(body) == 2
      assert Enum.all?(body, &(&1["author"] == "Alice"))
    end
  end

  describe "GET /books/:id" do
    test "returns a book by id" do
      {:ok, book} =
        BookApi.Books.create_book(%{title: "Found", author: "Author"})

      conn = call(:get, "/books/#{book.id}")
      assert conn.status == 200
      assert json_body(conn)["id"] == book.id
    end

    test "returns 404 for missing book" do
      conn = call(:get, "/books/999999")
      assert conn.status == 404
      assert json_body(conn)["error"] == "not found"
    end

    test "returns 404 for invalid id" do
      conn = call(:get, "/books/not-a-number")
      assert conn.status == 404
    end
  end

  describe "PUT /books/:id" do
    test "updates an existing book" do
      {:ok, book} =
        BookApi.Books.create_book(%{title: "Old", author: "Author"})

      conn = call(:put, "/books/#{book.id}", %{title: "New"})
      assert conn.status == 200
      assert json_body(conn)["title"] == "New"
    end

    test "returns 404 for missing book" do
      conn = call(:put, "/books/999999", %{title: "Foo"})
      assert conn.status == 404
    end

    test "rejects invalid update" do
      {:ok, book} = BookApi.Books.create_book(%{title: "X", author: "Y"})
      conn = call(:put, "/books/#{book.id}", %{title: ""})
      assert conn.status == 422
    end
  end

  describe "DELETE /books/:id" do
    test "deletes an existing book" do
      {:ok, book} = BookApi.Books.create_book(%{title: "Bye", author: "Author"})

      conn = call(:delete, "/books/#{book.id}")
      assert conn.status == 204
      assert conn.resp_body == ""

      assert BookApi.Books.get_book(book.id) == nil
    end

    test "returns 404 for missing book" do
      conn = call(:delete, "/books/999999")
      assert conn.status == 404
    end
  end
end
