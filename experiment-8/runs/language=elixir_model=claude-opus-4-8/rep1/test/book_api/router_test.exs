defmodule BookApi.Web.RouterTest do
  use BookApi.DataCase, async: false

  alias BookApi.Web.Router

  @opts Router.init([])

  defp request(method, path, body \\ nil) do
    conn =
      case body do
        nil -> conn(method, path)
        body -> conn(method, path, Jason.encode!(body)) |> put_req_header("content-type", "application/json")
      end

    Router.call(conn, @opts)
  end

  defp json(conn), do: Jason.decode!(conn.resp_body)

  describe "GET /health" do
    test "returns ok" do
      conn = request(:get, "/health")
      assert conn.status == 200
      assert json(conn) == %{"status" => "ok"}
    end
  end

  describe "POST /books" do
    test "creates a book with valid params" do
      conn = request(:post, "/books", %{title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441013593"})

      assert conn.status == 201
      body = json(conn)
      assert body["id"]
      assert body["title"] == "Dune"
      assert body["author"] == "Frank Herbert"
      assert body["year"] == 1965
    end

    test "rejects missing required fields with 422" do
      conn = request(:post, "/books", %{year: 1965})

      assert conn.status == 422
      errors = json(conn)["errors"]
      assert errors["title"] == ["can't be blank"]
      assert errors["author"] == ["can't be blank"]
    end
  end

  describe "GET /books" do
    test "lists books and filters by author" do
      request(:post, "/books", %{title: "Dune", author: "Frank Herbert"})
      request(:post, "/books", %{title: "Foundation", author: "Isaac Asimov"})

      all = request(:get, "/books") |> json()
      assert length(all) == 2

      filtered = request(:get, "/books?author=asimov") |> json()
      assert length(filtered) == 1
      assert hd(filtered)["title"] == "Foundation"
    end
  end

  describe "GET /books/:id" do
    test "returns a book by id" do
      created = request(:post, "/books", %{title: "1984", author: "George Orwell"}) |> json()
      conn = request(:get, "/books/#{created["id"]}")

      assert conn.status == 200
      assert json(conn)["title"] == "1984"
    end

    test "returns 404 for unknown id" do
      conn = request(:get, "/books/999999")
      assert conn.status == 404
    end
  end

  describe "PUT /books/:id" do
    test "updates an existing book" do
      created = request(:post, "/books", %{title: "Old", author: "Author"}) |> json()
      conn = request(:put, "/books/#{created["id"]}", %{title: "New Title"})

      assert conn.status == 200
      assert json(conn)["title"] == "New Title"
    end

    test "returns 404 when updating a missing book" do
      conn = request(:put, "/books/999999", %{title: "Nope"})
      assert conn.status == 404
    end
  end

  describe "DELETE /books/:id" do
    test "deletes a book" do
      created = request(:post, "/books", %{title: "Temp", author: "Author"}) |> json()
      conn = request(:delete, "/books/#{created["id"]}")
      assert conn.status == 204

      conn = request(:get, "/books/#{created["id"]}")
      assert conn.status == 404
    end
  end
end
