defmodule BookApi.RouterTest do
  use ExUnit.Case, async: false
  import Plug.Conn
  import Plug.Test

  alias BookApi.{DB, Router}

  @opts Router.init([])

  setup do
    {:ok, _} = DB.query("DELETE FROM books")
    :ok
  end

  defp request(method, path, body \\ nil) do
    conn =
      case body do
        nil -> conn(method, path)
        map -> conn(method, path, Jason.encode!(map)) |> put_req_header("content-type", "application/json")
      end

    Router.call(conn, @opts)
  end

  defp json_body(conn), do: Jason.decode!(conn.resp_body)

  @dune %{"title" => "Dune", "author" => "Frank Herbert", "year" => 1965, "isbn" => "9780441172719"}

  test "GET /health reports ok" do
    conn = request(:get, "/health")
    assert conn.status == 200
    assert json_body(conn) == %{"status" => "ok"}
  end

  test "full CRUD lifecycle over HTTP" do
    created = request(:post, "/books", @dune)
    assert created.status == 201
    %{"id" => id} = book = json_body(created)
    assert book["title"] == "Dune"

    assert request(:get, "/books/#{id}").status == 200

    updated = request(:put, "/books/#{id}", %{"title" => "Dune", "author" => "Herbert, Frank", "year" => 1965})
    assert updated.status == 200
    assert json_body(updated)["author"] == "Herbert, Frank"

    assert request(:delete, "/books/#{id}").status == 204
    assert request(:get, "/books/#{id}").status == 404
  end

  test "POST rejects missing title and author with 422" do
    conn = request(:post, "/books", %{"year" => 2020})
    assert conn.status == 422
    assert %{"error" => "validation_failed", "details" => details} = json_body(conn)
    assert details["title"] && details["author"]
  end

  test "GET /books supports ?author= filter" do
    request(:post, "/books", @dune)
    request(:post, "/books", %{"title" => "Emma", "author" => "Jane Austen"})

    conn = request(:get, "/books?author=Jane%20Austen")
    assert conn.status == 200
    assert [%{"title" => "Emma"}] = json_body(conn)
  end

  test "invalid ids and malformed JSON are handled" do
    assert request(:get, "/books/abc").status == 404

    conn =
      conn(:post, "/books", "{not json")
      |> put_req_header("content-type", "application/json")
      |> Router.call(@opts)

    assert conn.status == 400
    assert json_body(conn) == %{"error" => "invalid_json"}
  end

  test "unknown routes return 404 JSON" do
    conn = request(:get, "/nope")
    assert conn.status == 404
    assert json_body(conn) == %{"error" => "not_found"}
  end
end
