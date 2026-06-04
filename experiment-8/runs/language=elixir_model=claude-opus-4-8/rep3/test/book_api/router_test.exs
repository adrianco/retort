defmodule BookApi.RouterTest do
  use BookApi.DataCase

  alias BookApi.Router

  @opts Router.init([])

  defp call(method, path, body \\ nil) do
    conn =
      case body do
        nil ->
          conn(method, path)

        body ->
          conn(method, path, Jason.encode!(body))
          |> put_req_header("content-type", "application/json")
      end

    Router.call(conn, @opts)
  end

  test "GET /health returns ok" do
    conn = call(:get, "/health")
    assert conn.status == 200
    assert Jason.decode!(conn.resp_body) == %{"status" => "ok"}
  end

  test "POST /books creates a book" do
    conn = call(:post, "/books", %{title: "1984", author: "George Orwell", year: 1949})
    assert conn.status == 201
    body = Jason.decode!(conn.resp_body)
    assert body["title"] == "1984"
    assert body["id"]
  end

  test "POST /books validates required fields" do
    conn = call(:post, "/books", %{year: 2000})
    assert conn.status == 422
    body = Jason.decode!(conn.resp_body)
    assert body["errors"]["title"]
    assert body["errors"]["author"]
  end

  test "GET /books lists books and filters by author" do
    call(:post, "/books", %{title: "A", author: "Alice"})
    call(:post, "/books", %{title: "B", author: "Bob"})

    conn = call(:get, "/books")
    assert conn.status == 200
    assert length(Jason.decode!(conn.resp_body)) == 2

    conn = call(:get, "/books?author=Alice")
    body = Jason.decode!(conn.resp_body)
    assert length(body) == 1
    assert hd(body)["author"] == "Alice"
  end

  test "GET /books/:id returns a book or 404" do
    conn = call(:post, "/books", %{title: "X", author: "Y"})
    id = Jason.decode!(conn.resp_body)["id"]

    conn = call(:get, "/books/#{id}")
    assert conn.status == 200
    assert Jason.decode!(conn.resp_body)["id"] == id

    conn = call(:get, "/books/999999")
    assert conn.status == 404
  end

  test "PUT /books/:id updates a book" do
    conn = call(:post, "/books", %{title: "Old", author: "Author"})
    id = Jason.decode!(conn.resp_body)["id"]

    conn = call(:put, "/books/#{id}", %{title: "New"})
    assert conn.status == 200
    assert Jason.decode!(conn.resp_body)["title"] == "New"
  end

  test "DELETE /books/:id removes a book" do
    conn = call(:post, "/books", %{title: "Temp", author: "Author"})
    id = Jason.decode!(conn.resp_body)["id"]

    conn = call(:delete, "/books/#{id}")
    assert conn.status == 204

    conn = call(:get, "/books/#{id}")
    assert conn.status == 404
  end
end
