defmodule BookApi.RouterTest do
  use BookApi.DataCase, async: false
  import Plug.Test
  import Plug.Conn

  alias BookApi.Router

  @opts Router.init([])

  defp json_conn(method, path, body) do
    conn(method, path, Jason.encode!(body))
    |> put_req_header("content-type", "application/json")
  end

  describe "GET /health" do
    test "returns 200 with status ok" do
      conn = conn(:get, "/health") |> Router.call(@opts)
      assert conn.status == 200
      assert Jason.decode!(conn.resp_body) == %{"status" => "ok"}
    end
  end

  describe "POST /books" do
    test "creates a book with valid data" do
      conn =
        json_conn(:post, "/books", %{
          "title" => "1984",
          "author" => "George Orwell",
          "year" => 1949,
          "isbn" => "9780451524935"
        })
        |> Router.call(@opts)

      assert conn.status == 201
      body = Jason.decode!(conn.resp_body)
      assert body["title"] == "1984"
      assert body["author"] == "George Orwell"
      assert is_integer(body["id"])
    end

    test "returns 422 when required fields are missing" do
      conn = json_conn(:post, "/books", %{"year" => 1949}) |> Router.call(@opts)
      assert conn.status == 422
      body = Jason.decode!(conn.resp_body)
      assert body["errors"]["title"] == ["can't be blank"]
      assert body["errors"]["author"] == ["can't be blank"]
    end
  end

  describe "GET /books" do
    test "lists all books and filters by author" do
      json_conn(:post, "/books", %{"title" => "A", "author" => "Alice"}) |> Router.call(@opts)
      json_conn(:post, "/books", %{"title" => "B", "author" => "Bob"}) |> Router.call(@opts)

      conn = conn(:get, "/books") |> Router.call(@opts)
      assert conn.status == 200
      assert length(Jason.decode!(conn.resp_body)) == 2

      conn = conn(:get, "/books?author=Alice") |> Router.call(@opts)
      assert conn.status == 200
      results = Jason.decode!(conn.resp_body)
      assert length(results) == 1
      assert hd(results)["author"] == "Alice"
    end
  end

  describe "GET /books/:id" do
    test "returns a single book" do
      post_conn =
        json_conn(:post, "/books", %{"title" => "Dune", "author" => "Frank Herbert"})
        |> Router.call(@opts)

      id = Jason.decode!(post_conn.resp_body)["id"]

      conn = conn(:get, "/books/#{id}") |> Router.call(@opts)
      assert conn.status == 200
      assert Jason.decode!(conn.resp_body)["title"] == "Dune"
    end

    test "returns 404 for unknown book" do
      conn = conn(:get, "/books/99999") |> Router.call(@opts)
      assert conn.status == 404
    end
  end

  describe "PUT /books/:id" do
    test "updates an existing book" do
      post_conn =
        json_conn(:post, "/books", %{"title" => "Dune", "author" => "Frank Herbert"})
        |> Router.call(@opts)

      id = Jason.decode!(post_conn.resp_body)["id"]

      conn =
        json_conn(:put, "/books/#{id}", %{"title" => "Dune Messiah"})
        |> Router.call(@opts)

      assert conn.status == 200
      assert Jason.decode!(conn.resp_body)["title"] == "Dune Messiah"
    end

    test "returns 404 when updating unknown book" do
      conn =
        json_conn(:put, "/books/99999", %{"title" => "x"})
        |> Router.call(@opts)

      assert conn.status == 404
    end
  end

  describe "DELETE /books/:id" do
    test "deletes a book" do
      post_conn =
        json_conn(:post, "/books", %{"title" => "Dune", "author" => "Frank Herbert"})
        |> Router.call(@opts)

      id = Jason.decode!(post_conn.resp_body)["id"]

      conn = conn(:delete, "/books/#{id}") |> Router.call(@opts)
      assert conn.status == 204

      conn = conn(:get, "/books/#{id}") |> Router.call(@opts)
      assert conn.status == 404
    end

    test "returns 404 deleting unknown book" do
      conn = conn(:delete, "/books/99999") |> Router.call(@opts)
      assert conn.status == 404
    end
  end
end
