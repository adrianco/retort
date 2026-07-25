defmodule BooksApi.RouterTest do
  use BooksApi.DataCase, async: false
  import Plug.Test
  import Plug.Conn

  alias BooksApi.Router

  @opts Router.init([])

  defp request(method, path, body \\ nil) do
    conn =
      if body do
        method
        |> conn(path, Jason.encode!(body))
        |> put_req_header("content-type", "application/json")
      else
        conn(method, path)
      end

    Router.call(conn, @opts)
  end

  defp json_body(conn), do: Jason.decode!(conn.resp_body)

  test "GET /health returns ok" do
    conn = request(:get, "/health")
    assert conn.status == 200
    assert json_body(conn) == %{"status" => "ok"}
  end

  test "POST /books creates a book and returns 201" do
    conn =
      request(:post, "/books", %{
        title: "Release It!",
        author: "Michael Nygard",
        year: 2007,
        isbn: "978-1680502398"
      })

    assert conn.status == 201
    body = json_body(conn)
    assert body["id"]
    assert body["title"] == "Release It!"
    assert body["author"] == "Michael Nygard"
    assert body["year"] == 2007
    assert body["isbn"] == "978-1680502398"
  end

  test "POST /books without title/author returns 422 with errors" do
    conn = request(:post, "/books", %{year: 2020})

    assert conn.status == 422
    body = json_body(conn)
    assert body["errors"]["title"] == ["can't be blank"]
    assert body["errors"]["author"] == ["can't be blank"]
  end

  test "GET /books lists books and supports ?author= filter" do
    request(:post, "/books", %{title: "A", author: "Alice"})
    request(:post, "/books", %{title: "B", author: "Bob"})
    request(:post, "/books", %{title: "C", author: "Alice"})

    conn = request(:get, "/books")
    assert conn.status == 200
    assert length(json_body(conn)) == 3

    conn = request(:get, "/books?author=Alice")
    assert conn.status == 200
    body = json_body(conn)
    assert length(body) == 2
    assert Enum.all?(body, &(&1["author"] == "Alice"))
  end

  test "GET /books/:id returns the book or 404" do
    created = json_body(request(:post, "/books", %{title: "Solo", author: "Ann"}))

    conn = request(:get, "/books/#{created["id"]}")
    assert conn.status == 200
    assert json_body(conn)["title"] == "Solo"

    assert request(:get, "/books/999999").status == 404
    assert request(:get, "/books/not-an-id").status == 404
  end

  test "PUT /books/:id updates a book" do
    created = json_body(request(:post, "/books", %{title: "Draft", author: "Ann"}))

    conn = request(:put, "/books/#{created["id"]}", %{title: "Final", year: 2024})
    assert conn.status == 200
    body = json_body(conn)
    assert body["title"] == "Final"
    assert body["year"] == 2024
    assert body["author"] == "Ann"

    conn = request(:put, "/books/#{created["id"]}", %{title: ""})
    assert conn.status == 422

    assert request(:put, "/books/999999", %{title: "X"}).status == 404
  end

  test "DELETE /books/:id deletes a book" do
    created = json_body(request(:post, "/books", %{title: "Temp", author: "Ann"}))

    conn = request(:delete, "/books/#{created["id"]}")
    assert conn.status == 204

    assert request(:get, "/books/#{created["id"]}").status == 404
    assert request(:delete, "/books/#{created["id"]}").status == 404
  end
end
