defmodule BookApiTest do
  use ExUnit.Case, async: false
  import Plug.Test
  import Plug.Conn

  alias BookApi.{Book, Router, Store}

  @dune %{
    "title" => "Dune",
    "author" => "Frank Herbert",
    "year" => 1965,
    "isbn" => "9780441172719"
  }

  setup do
    Store.delete_all()
  end

  defp request(method, path, body \\ nil) do
    conn =
      if body do
        body = if is_binary(body), do: body, else: Jason.encode!(body)
        method |> conn(path, body) |> put_req_header("content-type", "application/json")
      else
        conn(method, path)
      end

    conn =
      try do
        Router.call(conn, Router.init([]))
      rescue
        # Plug.ErrorHandler sends the response, then re-raises.
        _ ->
          receive do
            {:plug_conn, :sent} -> :ok
          after
            0 -> :ok
          end

          {status, headers, resp_body} = sent_resp(conn)
          %{conn | status: status, resp_headers: headers, resp_body: resp_body}
      end

    decoded = if conn.resp_body == "", do: nil, else: Jason.decode!(conn.resp_body)
    {conn.status, decoded, conn}
  end

  defp create!(attrs) do
    {201, book, _} = request(:post, "/books", attrs)
    book
  end

  test "GET /health" do
    assert {200, %{"status" => "ok"}, conn} = request(:get, "/health")
    assert get_resp_header(conn, "content-type") == ["application/json; charset=utf-8"]
  end

  describe "POST /books" do
    test "creates a book" do
      assert {201, book, _} = request(:post, "/books", @dune)
      assert is_integer(book["id"])
      assert Map.delete(book, "id") == @dune
    end

    test "year and isbn are optional" do
      assert {201, book, _} = request(:post, "/books", %{"title" => "T", "author" => "A"})
      assert book["year"] == nil
      assert book["isbn"] == nil
    end

    test "requires title and author" do
      assert {422, body, _} = request(:post, "/books", %{"year" => 2000})
      assert body["details"] == %{"title" => "is required", "author" => "is required"}
      assert {200, [], _} = request(:get, "/books")
    end

    test "rejects blank title and wrongly typed fields" do
      assert {422, body, _} =
               request(:post, "/books", %{
                 "title" => "  ",
                 "author" => 5,
                 "year" => "x",
                 "isbn" => 1
               })

      assert Map.keys(body["details"]) == ["author", "isbn", "title", "year"]
    end

    test "rejects malformed JSON" do
      assert {400, %{"error" => "invalid JSON"}, _} = request(:post, "/books", "{nope")
    end

    test "rejects a non-object body" do
      assert {400, _, _} = request(:post, "/books", "[1]")
    end

    test "rejects a missing body" do
      assert {422, _, _} = request(:post, "/books")
    end
  end

  describe "GET /books" do
    test "lists all books" do
      a = create!(@dune)
      b = create!(%{"title" => "Emma", "author" => "Jane Austen"})
      assert {200, [^a, ^b], _} = request(:get, "/books")
    end

    test "filters by author" do
      create!(@dune)
      emma = create!(%{"title" => "Emma", "author" => "Jane Austen"})

      assert {200, [^emma], _} = request(:get, "/books?author=Jane%20Austen")
      assert {200, [^emma], _} = request(:get, "/books?author=jane+austen")
      assert {200, [], _} = request(:get, "/books?author=Nobody")
    end
  end

  describe "GET /books/:id" do
    test "returns the book" do
      book = create!(@dune)
      assert {200, ^book, _} = request(:get, "/books/#{book["id"]}")
    end

    test "404 for unknown or invalid id" do
      assert {404, %{"error" => _}, _} = request(:get, "/books/999")
      assert {404, _, _} = request(:get, "/books/abc")
      assert {404, _, _} = request(:get, "/books/99999999999999999999999")
    end
  end

  describe "PUT /books/:id" do
    test "updates the book" do
      %{"id" => id} = create!(@dune)
      update = %{"title" => "Dune Messiah", "author" => "Frank Herbert", "year" => 1969}

      assert {200, book, _} = request(:put, "/books/#{id}", update)

      assert book == %{
               "id" => id,
               "title" => "Dune Messiah",
               "author" => "Frank Herbert",
               "year" => 1969,
               "isbn" => nil
             }

      assert {200, ^book, _} = request(:get, "/books/#{id}")
    end

    test "validates input" do
      %{"id" => id} = book = create!(@dune)
      assert {422, _, _} = request(:put, "/books/#{id}", %{"title" => "Only title"})
      assert {200, ^book, _} = request(:get, "/books/#{id}")
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

  test "unknown route returns JSON 404" do
    assert {404, %{"error" => "not found"}, _} = request(:get, "/nope")
  end

  test "Book.validate/1 trims and normalises" do
    assert Book.validate(%{"title" => " T ", "author" => "A"}) ==
             {:ok, %{title: "T", author: "A", year: nil, isbn: nil}}
  end
end
