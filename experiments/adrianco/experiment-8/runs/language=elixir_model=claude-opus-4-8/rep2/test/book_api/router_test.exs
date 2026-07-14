defmodule BookApi.RouterTest do
  use BookApi.DataCase, async: false
  import Plug.Test
  import Plug.Conn

  alias BookApi.Router

  @opts Router.init([])

  defp request(method, path, body \\ nil) do
    conn =
      case body do
        nil -> conn(method, path)
        body -> conn(method, path, Jason.encode!(body)) |> put_req_header("content-type", "application/json")
      end

    Router.call(conn, @opts)
  end

  test "GET /health returns ok" do
    conn = request(:get, "/health")
    assert conn.status == 200
    assert Jason.decode!(conn.resp_body) == %{"status" => "ok"}
  end

  test "POST /books creates a book" do
    conn = request(:post, "/books", %{title: "1984", author: "George Orwell", year: 1949})
    assert conn.status == 201
    body = Jason.decode!(conn.resp_body)
    assert body["title"] == "1984"
    assert body["id"]
  end

  test "POST /books rejects missing required fields" do
    conn = request(:post, "/books", %{year: 2000})
    assert conn.status == 422
    body = Jason.decode!(conn.resp_body)
    assert body["errors"]["title"]
    assert body["errors"]["author"]
  end

  test "full CRUD lifecycle and author filter" do
    create = request(:post, "/books", %{title: "Neuromancer", author: "Gibson"})
    id = Jason.decode!(create.resp_body)["id"]

    show = request(:get, "/books/#{id}")
    assert show.status == 200

    list = request(:get, "/books?author=Gibson")
    assert list.status == 200
    assert length(Jason.decode!(list.resp_body)) == 1

    empty = request(:get, "/books?author=Nobody")
    assert Jason.decode!(empty.resp_body) == []

    update = request(:put, "/books/#{id}", %{title: "Count Zero"})
    assert update.status == 200
    assert Jason.decode!(update.resp_body)["title"] == "Count Zero"

    del = request(:delete, "/books/#{id}")
    assert del.status == 204

    missing = request(:get, "/books/#{id}")
    assert missing.status == 404
  end
end
