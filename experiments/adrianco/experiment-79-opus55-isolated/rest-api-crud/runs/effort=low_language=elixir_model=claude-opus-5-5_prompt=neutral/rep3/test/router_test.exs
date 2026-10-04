defmodule BookApi.RouterTest do
  use ExUnit.Case, async: false
  import Plug.Test
  import Plug.Conn

  alias BookApi.{Router, Store}

  @dune %{
    "title" => "Dune",
    "author" => "Frank Herbert",
    "year" => 1965,
    "isbn" => "9780441172719"
  }

  setup do
    Store.clear()
    :ok
  end

  defp request(method, path, body \\ nil) do
    payload = if is_nil(body) or is_binary(body), do: body, else: Jason.encode!(body)

    conn =
      method
      |> conn(path, payload)
      |> put_req_header("content-type", "application/json")
      |> Router.call(Router.init([]))

    decoded = if conn.resp_body == "", do: nil, else: Jason.decode!(conn.resp_body)
    {conn.status, decoded, conn}
  end

  defp create!(attrs) do
    {201, book, _} = request(:post, "/books", attrs)
    book
  end

  test "GET /health" do
    assert {200, %{"status" => "ok"}, conn} = request(:get, "/health")
    assert ["application/json" <> _] = get_resp_header(conn, "content-type")
  end

  describe "POST /books" do
    test "creates a book" do
      assert {201, book, _} = request(:post, "/books", @dune)
      assert is_integer(book["id"])
      assert Map.delete(book, "id") == @dune
    end

    test "year and isbn are optional" do
      assert {201, book, _} = request(:post, "/books", %{title: "T", author: "A"})
      assert book["year"] == nil
      assert book["isbn"] == nil
    end

    test "requires title and author" do
      assert {422, body, _} = request(:post, "/books", %{year: 1999})
      assert body["details"] == %{"title" => "is required", "author" => "is required"}
      assert {200, [], _} = request(:get, "/books")
    end

    test "rejects blank title and wrongly typed fields" do
      assert {422, body, _} =
               request(:post, "/books", %{title: "  ", author: "A", year: "x", isbn: 12})

      assert Map.keys(body["details"]) == ["isbn", "title", "year"]
    end

    test "rejects malformed JSON and non-object bodies" do
      assert {400, %{"error" => _}, _} = request(:post, "/books", "{nope")
      assert {422, _, _} = request(:post, "/books", "[1]")
    end
  end

  describe "GET /books" do
    test "lists all books" do
      a = create!(@dune)
      b = create!(%{title: "Emma", author: "Jane Austen"})
      assert {200, [^a, ^b], _} = request(:get, "/books")
    end

    test "filters by author" do
      create!(@dune)
      emma = create!(%{title: "Emma", author: "Jane Austen"})
      assert {200, [^emma], _} = request(:get, "/books?author=Jane%20Austen")
      assert {200, [], _} = request(:get, "/books?author=Nobody")
    end
  end

  describe "GET /books/:id" do
    test "returns the book" do
      book = create!(@dune)
      assert {200, ^book, _} = request(:get, "/books/#{book["id"]}")
    end

    test "404 for unknown or non-numeric id" do
      assert {404, %{"error" => _}, _} = request(:get, "/books/999")
      assert {404, _, _} = request(:get, "/books/abc")
    end
  end

  describe "PUT /books/:id" do
    test "updates the book" do
      %{"id" => id} = create!(@dune)
      update = %{"title" => "Dune Messiah", "author" => "Frank Herbert", "year" => 1969}

      assert {200, book, _} = request(:put, "/books/#{id}", update)
      assert book == Map.merge(update, %{"id" => id, "isbn" => nil})
      assert {200, ^book, _} = request(:get, "/books/#{id}")
    end

    test "validates input" do
      %{"id" => id} = create!(@dune)
      assert {422, _, _} = request(:put, "/books/#{id}", %{title: "No author"})
      assert {200, %{"title" => "Dune"}, _} = request(:get, "/books/#{id}")
    end

    test "404 for unknown id" do
      assert {404, _, _} = request(:put, "/books/999", @dune)
    end
  end

  describe "DELETE /books/:id" do
    test "deletes the book" do
      %{"id" => id} = create!(@dune)
      assert {204, nil, _} = request(:delete, "/books/#{id}")
      assert {404, _, _} = request(:get, "/books/#{id}")
      assert {404, _, _} = request(:delete, "/books/#{id}")
    end
  end

  test "unknown routes return 404 JSON" do
    assert {404, %{"error" => "not found"}, _} = request(:get, "/nope")
  end
end
