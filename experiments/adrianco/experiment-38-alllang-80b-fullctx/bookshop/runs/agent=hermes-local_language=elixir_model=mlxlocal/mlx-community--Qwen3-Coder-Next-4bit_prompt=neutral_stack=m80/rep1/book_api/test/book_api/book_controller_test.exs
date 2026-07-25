defmodule BookApi.BookControllerTest do
  use BookApi.Web.ConnCase, async: true

  alias BookApi.Repo
  alias BookApi.Book

  setup do
    # Clean up database before each test
    Ecto.Adapters.SQL.query(Repo, "DELETE FROM books", [])
    :ok
  end

  describe "GET /api/books" do
    test "returns all books", %{conn: conn} do
      # Create a test book
      {:ok, _book} = Repo.insert(%Book{title: "Test Book", author: "Test Author", year: 2024, isbn: "1234567890"})

      conn = get(conn, ~s{/api/books})
      assert json_response(conn, 200) =~ "Test Book"
    end

    test "filters by author", %{conn: conn} do
      # Create test books with different authors
      {:ok, _book1} = Repo.insert(%Book{title: "Book 1", author: "Author A", year: 2024, isbn: "1111111111"})
      {:ok, _book2} = Repo.insert(%Book{title: "Book 2", author: "Author B", year: 2024, isbn: "2222222222"})

      conn = get(conn, ~s{/api/books?author=Author%20A})
      response = json_response(conn, 200)

      assert response =~ "Book 1"
      refute response =~ "Book 2"
    end
  end

  describe "GET /api/books/:id" do
    test "returns a single book", %{conn: conn} do
      {:ok, book} = Repo.insert(%Book{title: "Test Book", author: "Test Author", year: 2024, isbn: "1234567890"})

      conn = get(conn, ~s{/api/books/#{book.id}})
      response = json_response(conn, 200)

      assert response =~ "Test Book"
      assert response =~ "Test Author"
    end

    test "returns 404 for non-existent book", %{conn: conn} do
      conn = get(conn, ~s{/api/books/9999})
      assert json_response(conn, 404) =~ "Book not found"
    end
  end

  describe "POST /api/books" do
    test "creates a new book", %{conn: conn} do
      attrs = %{title: "New Book", author: "New Author", year: 2024, isbn: "9999999999"}
      conn = post(conn, ~s{/api/books}, attrs)
      response = json_response(conn, 201)

      assert response =~ "New Book"
      assert response =~ "New Author"
    end

    test "returns errors for invalid data", %{conn: conn} do
      attrs = %{title: "New Book", year: 2024}
      conn = post(conn, ~s{/api/books}, attrs)
      response = json_response(conn, 422)

      assert response =~ "can't be blank"
      assert response =~ "author"
    end
  end

  describe "PUT /api/books/:id" do
    test "updates a book", %{conn: conn} do
      {:ok, book} = Repo.insert(%Book{title: "Old Title", author: "Old Author", year: 2020, isbn: "1111111111"})

      attrs = %{title: "Updated Title", author: "Updated Author", year: 2024, isbn: "1111111111"}
      conn = put(conn, ~s{/api/books/#{book.id}}, attrs)
      response = json_response(conn, 200)

      assert response =~ "Updated Title"
      assert response =~ "Updated Author"
    end

    test "returns 404 for non-existent book", %{conn: conn} do
      attrs = %{title: "Updated Title"}
      conn = put(conn, ~s{/api/books/9999}, attrs)
      assert json_response(conn, 404) =~ "Book not found"
    end
  end

  describe "DELETE /api/books/:id" do
    test "deletes a book", %{conn: conn} do
      {:ok, book} = Repo.insert(%Book{title: "To Delete", author: "Delete Author", year: 2024, isbn: "0000000001"})

      conn = delete(conn, ~s{/api/books/#{book.id}})
      assert json_response(conn, 204)

      # Verify book is deleted
      conn = get(conn, ~s{/api/books})
      response = json_response(conn, 200)
      refute response =~ "To Delete"
    end

    test "returns 404 for non-existent book", %{conn: conn} do
      conn = delete(conn, ~s{/api/books/9999})
      assert json_response(conn, 404) =~ "Book not found"
    end
  end

  describe "GET /api/health" do
    test "returns health status", %{conn: conn} do
      conn = get(conn, ~s{/api/health})
      response = json_response(conn, 200)

      assert response =~ "healthy"
    end
  end
end
