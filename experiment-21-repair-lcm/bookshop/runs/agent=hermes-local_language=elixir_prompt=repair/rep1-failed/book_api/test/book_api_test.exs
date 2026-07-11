defmodule BookApiTest do
  use ExUnit.Case

  import Plug.Conn
  import Plug.Test

  @endpoint BookApi.Router

  setup do
    # Truncate the books table for a clean state
    BookApi.Repo.query!("DELETE FROM books", [])

    # Build base connection for each test
    conn =
      conn("GET", "/")
      |> put_req_header("accept", "application/json")

    {:ok, conn: conn}
  end

  describe "POST /books" do
    test "creates a book with all fields", %{conn: conn} do
      body = Jason.encode!(%{
        title: "The Great Gatsby",
        author: "F. Scott Fitzgerald",
        year: 1925,
        isbn: "978-0743273565"
      })

      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> post("/books", body)

      assert conn.status == 201
      response = json_response(conn, 201)
      assert response["title"] == "The Great Gatsby"
      assert response["author"] == "F. Scott Fitzgerald"
      assert response["year"] == 1925
      assert response["isbn"] == "978-0743273565"
      assert response["id"] == 1
    end

    test "creates a book with partial fields", %{conn: conn} do
      body = Jason.encode!(%{
        title: "Testing Elixir",
        author: "Jose Valim"
      })

      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> post("/books", body)

      assert conn.status == 201
      response = json_response(conn, 201)
      assert response["title"] == "Testing Elixir"
      assert response["author"] == "Jose Valim"
      assert response["year"] == nil
      assert response["isbn"] == nil
    end

    test "rejects creation without title", %{conn: conn} do
      body = Jason.encode!(%{
        author: "Unknown Author",
        year: 2020
      })

      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> post("/books", body)

      assert conn.status == 400
      response = json_response(conn, 400)
      assert response["error"] == "Validation failed"
    end

    test "rejects creation without author", %{conn: conn} do
      body = Jason.encode!(%{
        title: "Unknown Title",
        year: 2020
      })

      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> post("/books", body)

      assert conn.status == 400
      response = json_response(conn, 400)
      assert response["error"] == "Validation failed"
    end

    test "rejects creation without title and author", %{conn: conn} do
      body = Jason.encode!(%{
        year: 2020
      })

      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> post("/books", body)

      assert conn.status == 400
      response = json_response(conn, 400)
      assert response["error"] == "Validation failed"
    end
  end

  describe "GET /books" do
    test "lists all books", %{conn: conn} do
      # Create some books first
      BookApi.Repo.insert!(%BookApi.Books.Book{
        title: "Book 1",
        author: "Author A",
        year: 2020,
        isbn: "111"
      })

      BookApi.Repo.insert!(%BookApi.Books.Book{
        title: "Book 2",
        author: "Author B",
        year: 2021,
        isbn: "222"
      })

      conn =
        conn
        |> get("/books")

      assert conn.status == 200
      response = json_response(conn, 200)
      assert length(response["books"]) == 2
      titles = Enum.map(response["books"], & &1["title"])
      assert "Book 1" in titles
      assert "Book 2" in titles
    end

    test "lists empty when no books", %{conn: conn} do
      conn =
        conn
        |> get("/books")

      assert conn.status == 200
      response = json_response(conn, 200)
      assert response["books"] == []
    end

    test "filters books by author", %{conn: conn} do
      # Create some books with different authors
      BookApi.Repo.insert!(%BookApi.Books.Book{
        title: "Book 1",
        author: "George Orwell",
        year: 1949,
        isbn: "111"
      })

      BookApi.Repo.insert!(%BookApi.Books.Book{
        title: "Book 2",
        author: "George Orwell",
        year: 1984,
        isbn: "222"
      })

      BookApi.Repo.insert!(%BookApi.Books.Book{
        title: "Book 3",
        author: "Aldous Huxley",
        year: 1932,
        isbn: "333"
      })

      conn =
        conn
        |> get("/books?author=George Orwell")

      assert conn.status == 200
      response = json_response(conn, 200)
      assert length(response["books"]) == 2
      authors = Enum.map(response["books"], & &1["author"])
      assert Enum.all?(authors, &(&1 == "George Orwell"))
    end
  end

  describe "GET /books/:id" do
    test "returns a book by id", %{conn: conn} do
      book = BookApi.Repo.insert!(%BookApi.Books.Book{
        title: "1984",
        author: "George Orwell",
        year: 1949,
        isbn: "111"
      })

      conn =
        conn
        |> get("/books/#{book.id}")

      assert conn.status == 200
      response = json_response(conn, 200)
      assert response["id"] == book.id
      assert response["title"] == "1984"
      assert response["author"] == "George Orwell"
      assert response["year"] == 1949
    end

    test "returns 404 for non-existent book", %{conn: conn} do
      conn =
        conn
        |> get("/books/999")

      assert conn.status == 404
      response = json_response(conn, 404)
      assert response["error"] == "Book not found"
    end
  end

  describe "PUT /books/:id" do
    test "updates a book", %{conn: conn} do
      book = BookApi.Repo.insert!(%BookApi.Books.Book{
        title: "Original Title",
        author: "Original Author",
        year: 2000,
        isbn: "111"
      })

      body = Jason.encode!(%{
        title: "Updated Title",
        author: "Updated Author",
        year: 2020,
        isbn: "222"
      })

      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> put("/books/#{book.id}", body)

      assert conn.status == 200
      response = json_response(conn, 200)
      assert response["id"] == book.id
      assert response["title"] == "Updated Title"
      assert response["author"] == "Updated Author"
      assert response["year"] == 2020
      assert response["isbn"] == "222"
    end

    test "returns 404 for non-existent book", %{conn: conn} do
      body = Jason.encode!(%{
        title: "Updated Title",
        author: "Updated Author"
      })

      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> put("/books/999", body)

      assert conn.status == 404
      response = json_response(conn, 404)
      assert response["error"] == "Book not found"
    end

    test "returns 400 when validation fails", %{conn: conn} do
      book = BookApi.Repo.insert!(%BookApi.Books.Book{
        title: "Original Title",
        author: "Original Author",
        year: 2000
      })

      body = Jason.encode!(%{
        title: ""
      })

      conn =
        conn
        |> put_req_header("content-type", "application/json")
        |> put("/books/#{book.id}", body)

      assert conn.status == 400
      response = json_response(conn, 400)
      assert response["error"] == "Validation failed"
    end
  end

  describe "DELETE /books/:id" do
    test "deletes a book", %{conn: conn} do
      book = BookApi.Repo.insert!(%BookApi.Books.Book{
        title: "To Delete",
        author: "Author",
        year: 2020
      })

      conn =
        conn
        |> delete("/books/#{book.id}")

      assert conn.status == 200
      response = json_response(conn, 200)
      assert response["message"] == "Book deleted"

      # Verify it's actually deleted
      assert BookApi.Repo.get(BookApi.Books.Book, book.id) == nil
    end

    test "returns 404 for non-existent book", %{conn: conn} do
      conn =
        conn
        |> delete("/books/999")

      assert conn.status == 404
      response = json_response(conn, 404)
      assert response["error"] == "Book not found"
    end
  end

  describe "GET /health" do
    test "returns healthy status", %{conn: conn} do
      conn =
        conn
        |> get("/health")

      assert conn.status == 200
      response = json_response(conn, 200)
      assert response["status"] == "healthy"
    end
  end

  describe "Unknown routes" do
    test "returns 404 for unknown routes", %{conn: conn} do
      conn =
        conn
        |> get("/unknown")

      assert conn.status == 404
      response = json_response(conn, 404)
      assert response["error"] == "Not found"
    end
  end

  # Helper function to get JSON response
  defp json_response(conn, status) do
    assert conn.status == status
    assert conn.resp_headers["content-type"] =~ "application/json"
    Jason.decode!(conn.resp_body)
  end
end
