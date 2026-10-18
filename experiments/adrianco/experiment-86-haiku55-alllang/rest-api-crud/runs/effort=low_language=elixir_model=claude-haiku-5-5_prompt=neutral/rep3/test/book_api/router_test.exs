defmodule BookApi.Web.RouterTest do
  use ExUnit.Case, async: false
  import Plug.Test
  import Plug.Conn

  alias BookApi.{Repo, Book}
  alias BookApi.Web.Router

  @opts Router.init([])

  setup do
    Repo.delete_all(Book)
    :ok
  end

  defp call(method, path, body \\ nil) do
    conn =
      if body do
        conn(method, path, Jason.encode!(body))
        |> put_req_header("content-type", "application/json")
      else
        conn(method, path)
      end

    Router.call(conn, @opts)
  end

  defp json_body(conn), do: Jason.decode!(conn.resp_body)

  test "GET /health returns ok" do
    conn = call(:get, "/health")
    assert conn.status == 200
    assert json_body(conn) == %{"status" => "ok"}
  end

  test "full CRUD lifecycle" do
    created =
      call(:post, "/books", %{
        "title" => "Dune",
        "author" => "Frank Herbert",
        "year" => 1965,
        "isbn" => "123"
      })

    assert created.status == 201
    %{"id" => id} = json_body(created)

    fetched = call(:get, "/books/#{id}")
    assert fetched.status == 200
    assert %{"title" => "Dune", "year" => 1965} = json_body(fetched)

    updated = call(:put, "/books/#{id}", %{"year" => 1966})
    assert updated.status == 200
    assert %{"year" => 1966, "title" => "Dune"} = json_body(updated)

    deleted = call(:delete, "/books/#{id}")
    assert deleted.status == 204

    assert call(:get, "/books/#{id}").status == 404
  end

  test "POST rejects missing title and author with 422" do
    conn = call(:post, "/books", %{"year" => 2000})
    assert conn.status == 422
    body = json_body(conn)
    assert body["error"] == "validation failed"
    assert body["details"]["title"] == ["is required"]
    assert body["details"]["author"] == ["is required"]
  end

  test "POST with no JSON body returns 422 rather than crashing" do
    conn = conn(:post, "/books") |> Router.call(@opts)
    assert conn.status == 422
  end

  test "GET /books filters by author" do
    call(:post, "/books", %{"title" => "Dune", "author" => "Frank Herbert"})
    call(:post, "/books", %{"title" => "Emma", "author" => "Jane Austen"})

    all = json_body(call(:get, "/books"))
    assert length(all) == 2

    filtered = json_body(call(:get, "/books?author=Jane%20Austen"))
    assert [%{"title" => "Emma"}] = filtered
  end

  test "unknown ids and malformed ids return 404" do
    assert call(:get, "/books/999999").status == 404
    assert call(:get, "/books/abc").status == 404
    assert call(:put, "/books/999999", %{"title" => "x"}).status == 404
    assert call(:delete, "/books/999999").status == 404
  end

  test "PUT with invalid data returns 422" do
    {:ok, book} = BookApi.Books.create_book(%{"title" => "Dune", "author" => "FH"})
    conn = call(:put, "/books/#{book.id}", %{"title" => ""})
    assert conn.status == 422
  end

  test "unknown route returns 404 JSON" do
    conn = call(:get, "/nope")
    assert conn.status == 404
    assert json_body(conn) == %{"error" => "not found"}
  end
end
