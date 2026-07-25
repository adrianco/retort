defmodule BookAPIWeb.RouterTest do
  use ExUnit.Case, async: true

  alias BookAPI.Repo
  alias BookAPI.Books

  setup do
    :ok = Ecto.Adapters.SQL.Sandbox.checkout(BookAPI.Repo)
    Ecto.Adapters.SQL.Sandbox.mode(BookAPI.Repo, :manual)
    :ok
  end

  defp conn do
    Plug.Conn.build_conn(:plug, %Plug.Conn{}, nil)
  end

  defp post_json(conn, path, body) do
    conn
    |> Plug.Conn.put_req_header("content-type", "application/json")
    |> Plug.Conn.post(path, body)
  end

  defp put_json(conn, path, body) do
    conn
    |> Plug.Conn.put_req_header("content-type", "application/json")
    |> Plug.Conn.put(path, body)
  end

  defp json_response(conn, status \\ nil) do
    if status do
      assert {:ok, body} = conn.resp_body
      assert {:ok, json} = Jason.decode(body)
      json
    else
      assert {:ok, body} = conn.resp_body
      assert {:ok, json} = Jason.decode(body)
      json
    end
  end

  defp insert(:book, attrs \\ %{}) do
    {:ok, book} =
      attrs
      |> Map.put_new(:title, "Test Book")
      |> Map.put_new(:author, "Test Author")
      |> BookAPI.Books.create_book()

    book
  end

  describe "GET /health" do
    test "returns health check status" do
      conn = conn() |> Plug.Conn.get("/health")
      assert conn.status == 200
      assert Jason.decode!(conn.resp_body) == %{"status" => "ok"}
    end
  end

  describe "GET /books" do
    test "lists all books" do
      insert(:book, title: "Book 1", author: "Author A")
      insert(:book, title: "Book 2", author: "Author B")

      conn = conn() |> Plug.Conn.get("/books")
      assert conn.status == 200
      response = Jason.decode!(conn.resp_body)
      assert length(response["data"]) == 2
      assert response["data"][0]["title"] == "Book 1"
      assert response["data"][1]["title"] == "Book 2"
    end

    test "filters books by author" do
      insert(:book, title: "Book 1", author: "Author A")
      insert(:book, title: "Book 2", author: "Author B")
      insert(:book, title: "Book 3", author: "Author A")

      conn = conn() |> Plug.Conn.get("/books", author: "Author A")
      assert conn.status == 200
      response = Jason.decode!(conn.resp_body)
      assert length(response["data"]) == 2
      Enum.each(response["data"], fn d -> assert d["author"] == "Author A" end)
    end
  end

  describe "GET /books/:id" do
    test "shows chosen book" do
      book = insert(:book, title: "chosen book", author: "Author A", year: 2024, isbn: "1234567890")

      conn = conn() |> Plug.Conn.get("/books/#{book.id}")
      assert conn.status == 200
      response = Jason.decode!(conn.resp_body)
      assert response["data"]["title"] == "chosen book"
      assert response["data"]["author"] == "Author A"
      assert response["data"]["year"] == 2024
      assert response["data"]["isbn"] == "1234567890"
    end

    test "returns 404 when book not found" do
      conn = conn() |> Plug.Conn.get("/books/999999")
      assert conn.status == 404
      response = Jason.decode!(conn.resp_body)
      assert response["errors"]["detail"] == "Not Found"
    end
  end

  describe "POST /books" do
    test "creates book and returns chosen data" do
      attrs = %{
        "title" => "New Book",
        "author" => "New Author",
        "year" => 2024,
        "isbn" => "1234567890"
      }

      conn = conn() |> post_json("/books", Jason.encode!(attrs))
      assert conn.status == 201
      response = Jason.decode!(conn.resp_body)
      assert response["data"]["title"] == "New Book"
      assert response["data"]["author"] == "New Author"
      assert response["data"]["year"] == 2024
      assert response["data"]["isbn"] == "1234567890"
      assert response["data"]["id"]
    end

    test "returns errors when invalid data" do
      attrs = %{
        "author" => "New Author",
        "year" => 2024
      }

      conn = conn() |> post_json("/books", Jason.encode!(attrs))
      assert conn.status == 422
      response = Jason.decode!(conn.resp_body)
      assert response["errors"]
      assert response["errors"]["title"]
    end

    test "validates required fields" do
      attrs = %{
        "year" => 2024,
        "isbn" => "1234567890"
      }

      conn = conn() |> post_json("/books", Jason.encode!(attrs))
      assert conn.status == 422
      response = Jason.decode!(conn.resp_body)
      assert response["errors"]
      assert response["errors"]["title"]
      assert response["errors"]["author"]
    end
  end

  describe "PUT /books/:id" do
    test "updates chosen book" do
      book = insert(:book, title: "Old Title", author: "Old Author")

      attrs = %{
        "title" => "New Title",
        "author" => "New Author"
      }

      conn = conn() |> put_json("/books/#{book.id}", Jason.encode!(attrs))
      assert conn.status == 200
      response = Jason.decode!(conn.resp_body)
      assert response["data"]["title"] == "New Title"
      assert response["data"]["author"] == "New Author"
    end

    test "returns 404 when book not found" do
      attrs = %{
        "title" => "New Title"
      }

      conn = conn() |> put_json("/books/999999", Jason.encode!(attrs))
      assert conn.status == 404
      response = Jason.decode!(conn.resp_body)
      assert response["errors"]["detail"] == "Not Found"
    end
  end

  describe "DELETE /books/:id" do
    test "deletes chosen book" do
      book = insert(:book, title: "To Delete", author: "Delete Author")

      conn = conn() |> Plug.Conn.delete("/books/#{book.id}")
      assert conn.status == 204
      assert Books.list_books() == []
    end

    test "returns 404 when book not found" do
      conn = conn() |> Plug.Conn.delete("/books/999999")
      assert conn.status == 404
      response = Jason.decode!(conn.resp_body)
      assert response["errors"]["detail"] == "Not Found"
    end
  end
end
