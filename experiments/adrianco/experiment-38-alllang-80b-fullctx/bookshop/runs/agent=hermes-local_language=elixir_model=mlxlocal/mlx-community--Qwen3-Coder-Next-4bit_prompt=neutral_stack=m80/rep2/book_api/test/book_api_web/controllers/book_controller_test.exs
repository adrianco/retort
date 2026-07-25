defmodule BookApiWeb.BookControllerTest do
  use BookApiWeb.ConnCase, async: true

  alias BookApi.Book
  alias BookApi.Repo

  @create_attrs %{
    title: "Test Book",
    author: "Test Author",
    year: 2024,
    isbn: "1234567890"
  }
  @update_attrs %{
    title: "Updated Book",
    author: "Updated Author",
    year: 2025,
    isbn: "0987654321"
  }
  @invalid_attrs %{title: nil, author: nil}

  setup do
    :ok = Ecto.Adapters.SQL.Sandbox.checkout(Repo)
    Ecto.Adapters.SQL.Sandbox.mode(Repo, {:shared, self()})
    :ok
  end

  describe "index" do
    test "lists all books", %{conn: conn} do
      conn = get(conn, ~p"/api/books")
      assert json_response(conn, 200)["data"] == []
    end

    test "lists books filtered by author", %{conn: conn} do
      Repo.insert!(%Book{@create_attrs | author: "John Doe"})
      Repo.insert!(%Book{@create_attrs | author: "Jane Smith"})

      conn = get(conn, ~p"/api/books?author=John")
      assert json_response(conn, 200)["data"] |> length == 1
    end
  end

  describe "show" do
    setup [:create_book]

    test "shows chosen book", %{conn: conn, book: book} do
      conn = get(conn, ~p"/api/books/#{book.id}")
      assert json_response(conn, 200)["data"]["id"] == book.id
      assert json_response(conn, 200)["data"]["title"] == book.title
    end

    test "renders error when book not found", %{conn: conn} do
      conn = get(conn, ~p"/api/books/999999")
      assert json_response(conn, 404)
    end
  end

  describe "create" do
    test "creates and renders book when data is valid", %{conn: conn} do
      conn = post(conn, ~p"/api/books", %{"book" => @create_attrs})
      assert %{"data" => book_data} = json_response(conn, 201)

      assert book_data["title"] == "Test Book"
      assert book_data["author"] == "Test Author"
      assert book_data["year"] == 2024
      assert book_data["isbn"] == "1234567890"

      assert Repo.get_by(Book, %{title: "Test Book"})
    end

    test "renders errors when data is invalid", %{conn: conn} do
      conn = post(conn, ~p"/api/books", %{"book" => @invalid_attrs})
      assert json_response(conn, 422)
    end
  end

  describe "update" do
    setup [:create_book]

    test "updates and renders book when data is valid", %{conn: conn, book: book} do
      conn = put(conn, ~p"/api/books/#{book.id}", %{"book" => @update_attrs})
      assert %{"data" => book_data} = json_response(conn, 200)

      assert book_data["title"] == "Updated Book"
      assert book_data["author"] == "Updated Author"
      assert book_data["year"] == 2025
      assert book_data["isbn"] == "0987654321"
    end

    test "renders errors when data is invalid", %{conn: conn, book: book} do
      conn = put(conn, ~p"/api/books/#{book.id}", %{"book" => @invalid_attrs})
      assert json_response(conn, 422)
    end
  end

  describe "delete" do
    setup [:create_book]

    test "deletes chosen book", %{conn: conn, book: book} do
      conn = delete(conn, ~p"/api/books/#{book.id}")
      assert response(conn, 204)

      refute Repo.get(Book, book.id)
    end

    test "renders error when book not found", %{conn: conn} do
      conn = delete(conn, ~p"/api/books/999999")
      assert json_response(conn, 404)
    end
  end

  defp create_book(_) do
    book = Repo.insert!(%Book{@create_attrs})
    %{book: book}
  end
end
