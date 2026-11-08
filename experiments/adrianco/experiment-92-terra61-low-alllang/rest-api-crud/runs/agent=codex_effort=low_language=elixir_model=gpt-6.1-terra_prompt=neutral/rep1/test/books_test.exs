defmodule BooksTest do
  use ExUnit.Case, async: false
  import Plug.Test
  import Plug.Conn
  @opts Books.Router.init([])

  defp request(method, path, body \\ nil) do
    conn = conn(method, path, if(body == nil, do: "", else: Jason.encode!(body)))

    conn =
      if body == nil, do: conn, else: put_req_header(conn, "content-type", "application/json")

    Books.Router.call(conn, @opts)
  end

  defp data(conn), do: Jason.decode!(conn.resp_body)

  defp create(
         attrs \\ %{
           "title" => "Dune",
           "author" => "Frank Herbert",
           "year" => 1965,
           "isbn" => "123"
         }
       ) do
    request(:post, "/books", attrs)
  end

  setup do
    for book <- Books.Store.list(nil), do: Books.Store.delete(book.id)
    :ok
  end

  test "creates, retrieves, updates, and deletes a book" do
    created = create()
    assert created.status == 201
    book = data(created)
    id = book["id"]
    assert get_resp_header(created, "location") == ["/books/#{id}"]
    assert data(request(:get, "/books/#{id}")) == book
    updated = request(:put, "/books/#{id}", %{"title" => "New", "author" => "Writer"})
    assert updated.status == 200
    assert data(updated)["title"] == "New"
    assert data(updated)["year"] == nil
    assert request(:delete, "/books/#{id}").status == 204
    assert request(:get, "/books/#{id}").status == 404
    assert request(:delete, "/books/#{id}").status == 404
  end

  test "lists books and filters by exact author" do
    create()
    create(%{"title" => "Other", "author" => "Someone"})
    assert length(data(request(:get, "/books"))) == 2
    assert [%{"title" => "Dune"}] = data(request(:get, "/books?author=Frank%20Herbert"))
    assert data(request(:get, "/books?author=Nobody")) == []
  end

  test "validates required fields and optional field types" do
    response = create(%{"title" => " ", "year" => "no", "isbn" => 123})
    assert response.status == 422

    assert Map.keys(data(response)["errors"]) |> Enum.sort() == [
             "author",
             "isbn",
             "title",
             "year"
           ]

    assert request(:put, "/books/999", %{}).status == 404
    assert request(:get, "/books/not-an-id").status == 404
  end

  test "health and invalid JSON" do
    assert data(request(:get, "/health")) == %{"status" => "ok"}

    response =
      conn(:post, "/books", "{")
      |> put_req_header("content-type", "application/json")
      |> Books.Router.call(@opts)

    assert response.status == 400
    assert data(response)["error"] == "Invalid JSON"
  end
end
