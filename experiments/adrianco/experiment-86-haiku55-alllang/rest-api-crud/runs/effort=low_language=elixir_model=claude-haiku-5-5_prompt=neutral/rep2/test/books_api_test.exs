defmodule BooksApiTest do
  use ExUnit.Case, async: false

  import Plug.Test
  import Plug.Conn

  alias BooksApi.Router

  @opts Router.init([])

  setup do
    {:ok, _} = BooksApi.Repo.query("DELETE FROM books")
    :ok
  end

  defp call(method, path, body \\ nil) do
    conn =
      conn(method, path, body && Jason.encode!(body))
      |> put_req_header("content-type", "application/json")

    Router.call(conn, @opts)
  end

  defp json_body(conn), do: Jason.decode!(conn.resp_body)

  @valid %{
    "title" => "Dune",
    "author" => "Frank Herbert",
    "year" => 1965,
    "isbn" => "9780441013593"
  }

  test "health check" do
    conn = call(:get, "/health")
    assert conn.status == 200
    assert json_body(conn) == %{"status" => "ok"}
  end

  test "create, fetch, list, update and delete a book" do
    created = call(:post, "/books", @valid)
    assert created.status == 201
    book = json_body(created)
    assert book["title"] == "Dune"
    id = book["id"]

    fetched = call(:get, "/books/#{id}")
    assert fetched.status == 200
    assert json_body(fetched)["author"] == "Frank Herbert"

    listed = call(:get, "/books")
    assert listed.status == 200
    assert [%{"id" => ^id}] = json_body(listed)

    updated =
      call(:put, "/books/#{id}", %{"title" => "Dune Messiah", "author" => "Frank Herbert"})

    assert updated.status == 200
    assert json_body(updated)["title"] == "Dune Messiah"
    assert json_body(updated)["year"] == nil

    deleted = call(:delete, "/books/#{id}")
    assert deleted.status == 204

    assert call(:get, "/books/#{id}").status == 404
  end

  test "list filters by author" do
    call(:post, "/books", @valid)
    call(:post, "/books", %{"title" => "Emma", "author" => "Jane Austen"})

    filtered = Router.call(conn(:get, "/books?author=Jane%20Austen"), @opts)
    assert filtered.status == 200
    assert [%{"title" => "Emma"}] = json_body(filtered)
  end

  test "create rejects missing title and author with 422" do
    conn = call(:post, "/books", %{"year" => 2000})
    assert conn.status == 422
    details = json_body(conn)["details"]
    assert details["title"] == "is required"
    assert details["author"] == "is required"
  end

  test "create rejects blank strings and invalid year" do
    conn = call(:post, "/books", %{"title" => "  ", "author" => "A", "year" => "soon"})
    assert conn.status == 422
    details = json_body(conn)["details"]
    assert details["title"] == "must not be blank"
    assert details["year"] == "is invalid"
  end

  test "update validates input and returns 404 for unknown ids" do
    assert call(:put, "/books/99999", @valid).status == 404

    created = call(:post, "/books", @valid)
    id = json_body(created)["id"]
    assert call(:put, "/books/#{id}", %{"title" => ""}).status == 422
  end

  test "non-integer ids and unknown routes return 404" do
    assert call(:get, "/books/abc").status == 404
    assert call(:get, "/nope").status == 404
  end

  test "delete of unknown book returns 404" do
    assert call(:delete, "/books/99999").status == 404
  end
end
