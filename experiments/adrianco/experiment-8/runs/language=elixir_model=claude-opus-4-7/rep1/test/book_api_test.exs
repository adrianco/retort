defmodule BookApi.RouterTest do
  use ExUnit.Case, async: false
  import Plug.Test
  import Plug.Conn

  alias BookApi.Router
  alias BookApi.Repo

  @opts Router.init([])

  setup do
    Repo.reset!()
    :ok
  end

  defp json_request(method, path, body \\ nil) do
    conn = conn(method, path, body && Jason.encode!(body))

    conn =
      if body do
        put_req_header(conn, "content-type", "application/json")
      else
        conn
      end

    Router.call(conn, @opts)
  end

  defp decode(conn), do: Jason.decode!(conn.resp_body)

  test "GET /health returns 200" do
    conn = json_request(:get, "/health")
    assert conn.status == 200
    assert decode(conn) == %{"status" => "ok"}
  end

  test "POST /books creates a book and GET /books/:id returns it" do
    conn =
      json_request(:post, "/books", %{
        "title" => "Dune",
        "author" => "Frank Herbert",
        "year" => 1965,
        "isbn" => "978-0441172719"
      })

    assert conn.status == 201
    created = decode(conn)
    assert created["title"] == "Dune"
    assert created["author"] == "Frank Herbert"
    assert created["year"] == 1965
    assert is_integer(created["id"])

    conn = json_request(:get, "/books/#{created["id"]}")
    assert conn.status == 200
    assert decode(conn)["title"] == "Dune"
  end

  test "POST /books returns 422 when title or author missing" do
    conn = json_request(:post, "/books", %{"author" => "Anon"})
    assert conn.status == 422
    assert decode(conn)["errors"] == ["title is required"]

    conn = json_request(:post, "/books", %{"title" => "Untitled"})
    assert conn.status == 422
    assert decode(conn)["errors"] == ["author is required"]
  end

  test "GET /books filters by author" do
    json_request(:post, "/books", %{"title" => "A", "author" => "Alice"})
    json_request(:post, "/books", %{"title" => "B", "author" => "Bob"})
    json_request(:post, "/books", %{"title" => "C", "author" => "Alice"})

    conn = json_request(:get, "/books?author=Alice")
    assert conn.status == 200
    books = decode(conn)
    assert length(books) == 2
    assert Enum.all?(books, &(&1["author"] == "Alice"))

    conn = json_request(:get, "/books")
    assert length(decode(conn)) == 3
  end

  test "PUT /books/:id updates fields and DELETE removes the book" do
    create_conn =
      json_request(:post, "/books", %{"title" => "Old Title", "author" => "Someone"})

    id = decode(create_conn)["id"]

    conn =
      json_request(:put, "/books/#{id}", %{"title" => "New Title", "year" => 2020})

    assert conn.status == 200
    updated = decode(conn)
    assert updated["title"] == "New Title"
    assert updated["author"] == "Someone"
    assert updated["year"] == 2020

    conn = json_request(:delete, "/books/#{id}")
    assert conn.status == 204

    conn = json_request(:get, "/books/#{id}")
    assert conn.status == 404
  end

  test "GET /books/:id returns 404 for missing book" do
    conn = json_request(:get, "/books/99999")
    assert conn.status == 404
    assert decode(conn)["error"] == "book not found"
  end
end
