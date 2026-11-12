defmodule BookApiTest do
  use ExUnit.Case, async: false
  import Plug.Test
  import Plug.Conn

  alias BookApi.{Book, Router, Store}

  @opts Router.init([])
  @dune %{
    "title" => "Dune",
    "author" => "Frank Herbert",
    "year" => 1965,
    "isbn" => "9780441172719"
  }

  setup do
    Store.delete_all()
    :ok
  end

  defp call(method, path, body \\ nil) do
    payload = if is_map(body), do: JSON.encode!(body), else: body

    conn =
      method
      |> conn(path, payload)
      |> put_req_header("content-type", "application/json")
      |> Router.call(@opts)

    decoded = if conn.resp_body == "", do: nil, else: JSON.decode!(conn.resp_body)
    {conn.status, decoded, conn}
  end

  test "GET /health" do
    assert {200, %{"status" => "ok"}, conn} = call(:get, "/health")
    assert get_resp_header(conn, "content-type") == ["application/json; charset=utf-8"]
  end

  test "POST /books creates a book and GET returns it" do
    assert {201, %{"id" => id} = book, conn} = call(:post, "/books", @dune)
    assert Map.delete(book, "id") == @dune
    assert get_resp_header(conn, "location") == ["/books/#{id}"]
    assert {200, ^book, _} = call(:get, "/books/#{id}")
  end

  test "POST /books allows year and isbn to be omitted" do
    assert {201, %{"year" => nil, "isbn" => nil}, _} =
             call(:post, "/books", %{"title" => "T", "author" => "A"})
  end

  test "POST /books validates required fields" do
    assert {422, %{"details" => details}, _} = call(:post, "/books", %{"year" => 2000})
    assert details == %{"title" => "is required", "author" => "is required"}

    assert {422, %{"details" => %{"title" => _}}, _} =
             call(:post, "/books", %{"title" => "  ", "author" => "A"})

    assert {422, %{"details" => %{"year" => _}}, _} =
             call(:post, "/books", Map.put(@dune, "year", "old"))

    assert {200, [], _} = call(:get, "/books")
  end

  test "POST /books rejects malformed and non-object JSON" do
    assert {400, %{"error" => _}, _} = call(:post, "/books", "{not json")
    assert {422, _, _} = call(:post, "/books", "[1,2]")
  end

  test "GET /books lists all books and filters by author" do
    {201, _, _} = call(:post, "/books", @dune)
    {201, _, _} = call(:post, "/books", %{"title" => "Emma", "author" => "Jane Austen"})
    {201, _, _} = call(:post, "/books", %{"title" => "Persuasion", "author" => "Jane Austen"})

    assert {200, all, _} = call(:get, "/books")
    assert length(all) == 3

    assert {200, austen, _} = call(:get, "/books?author=Jane%20Austen")
    assert Enum.map(austen, & &1["title"]) == ["Emma", "Persuasion"]

    assert {200, [], _} = call(:get, "/books?author=Nobody")
  end

  test "GET /books/:id returns 404 for unknown or invalid ids" do
    assert {404, %{"error" => _}, _} = call(:get, "/books/999")
    assert {404, _, _} = call(:get, "/books/abc")
  end

  test "PUT /books/:id updates a book" do
    {201, %{"id" => id}, _} = call(:post, "/books", @dune)
    updated = %{"title" => "Dune Messiah", "author" => "Frank Herbert", "year" => 1969}

    assert {200, book, _} = call(:put, "/books/#{id}", updated)

    assert book == %{
             "id" => id,
             "title" => "Dune Messiah",
             "author" => "Frank Herbert",
             "year" => 1969,
             "isbn" => nil
           }

    assert {200, ^book, _} = call(:get, "/books/#{id}")
  end

  test "PUT /books/:id validates input and handles missing books" do
    {201, %{"id" => id}, _} = call(:post, "/books", @dune)
    assert {422, _, _} = call(:put, "/books/#{id}", %{"title" => "No author"})
    assert {200, %{"title" => "Dune"}, _} = call(:get, "/books/#{id}")
    assert {404, _, _} = call(:put, "/books/999", @dune)
  end

  test "DELETE /books/:id removes a book" do
    {201, %{"id" => id}, _} = call(:post, "/books", @dune)
    assert {204, nil, _} = call(:delete, "/books/#{id}")
    assert {404, _, _} = call(:get, "/books/#{id}")
    assert {404, _, _} = call(:delete, "/books/#{id}")
  end

  test "unknown routes return 404 JSON" do
    assert {404, %{"error" => "not found"}, _} = call(:get, "/nope")
  end

  test "Book.validate/1 trims strings" do
    assert {:ok, %{title: "T", author: "A", year: nil, isbn: nil}} =
             Book.validate(%{"title" => " T ", "author" => "A "})
  end
end
