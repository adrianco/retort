defmodule BookApiTest do
  use ExUnit.Case, async: false
  import Plug.Test
  import Plug.Conn

  alias BookApi.{Router, Store}

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

  defp request(method, path, body \\ nil) do
    conn =
      if body do
        body = if is_binary(body), do: body, else: Jason.encode!(body)
        method |> conn(path, body) |> put_req_header("content-type", "application/json")
      else
        conn(method, path)
      end

    # Plug.ErrorHandler re-raises after sending the error response.
    conn =
      try do
        Router.call(conn, @opts)
      rescue
        _ ->
          assert_received {:plug_conn, :sent}
          {status, headers, body} = sent_resp(conn)
          %{conn | status: status, resp_headers: headers, resp_body: body}
      end

    {conn.status, if(conn.resp_body == "", do: nil, else: Jason.decode!(conn.resp_body))}
  end

  defp create!(attrs) do
    {201, book} = request(:post, "/books", attrs)
    book
  end

  test "GET /health" do
    assert {200, %{"status" => "ok"}} = request(:get, "/health")
  end

  describe "POST /books" do
    test "creates a book" do
      assert {201, book} = request(:post, "/books", @dune)
      assert is_integer(book["id"])
      assert Map.delete(book, "id") == @dune
    end

    test "year and isbn are optional" do
      assert {201, %{"year" => nil, "isbn" => nil}} =
               request(:post, "/books", %{"title" => "T", "author" => "A"})
    end

    test "requires title and author" do
      assert {422, %{"details" => details}} = request(:post, "/books", %{"year" => 1999})
      assert details == %{"title" => "is required", "author" => "is required"}
    end

    test "rejects blank title and wrongly typed fields" do
      body = %{"title" => "  ", "author" => 7, "year" => "soon", "isbn" => 1}
      assert {422, %{"details" => details}} = request(:post, "/books", body)
      assert Map.keys(details) == ["author", "isbn", "title", "year"]
    end

    test "rejects malformed JSON" do
      assert {400, %{"error" => _}} = request(:post, "/books", "{not json")
    end

    test "rejects a non-object body" do
      assert {422, _} = request(:post, "/books", [1, 2])
    end
  end

  describe "GET /books" do
    test "lists all books" do
      assert {200, []} = request(:get, "/books")
      create!(@dune)
      create!(%{"title" => "Emma", "author" => "Jane Austen"})
      assert {200, [%{"title" => "Dune"}, %{"title" => "Emma"}]} = request(:get, "/books")
    end

    test "filters by author" do
      create!(@dune)
      create!(%{"title" => "Emma", "author" => "Jane Austen"})

      assert {200, [%{"title" => "Emma"}]} = request(:get, "/books?author=Jane%20Austen")
      assert {200, [%{"title" => "Dune"}]} = request(:get, "/books?author=frank+herbert")
      assert {200, []} = request(:get, "/books?author=Nobody")
    end
  end

  describe "GET /books/:id" do
    test "returns the book" do
      book = create!(@dune)
      assert {200, ^book} = request(:get, "/books/#{book["id"]}")
    end

    test "404 for unknown or invalid id" do
      assert {404, %{"error" => "Book not found"}} = request(:get, "/books/999")
      assert {404, _} = request(:get, "/books/abc")
    end
  end

  describe "PUT /books/:id" do
    test "updates the book" do
      %{"id" => id} = create!(@dune)
      update = %{"title" => "Dune Messiah", "author" => "Frank Herbert", "year" => 1969}

      assert {200, updated} = request(:put, "/books/#{id}", update)

      assert updated == %{
               "id" => id,
               "title" => "Dune Messiah",
               "author" => "Frank Herbert",
               "year" => 1969,
               "isbn" => nil
             }

      assert {200, ^updated} = request(:get, "/books/#{id}")
    end

    test "validates input" do
      %{"id" => id} = create!(@dune)

      assert {422, %{"details" => %{"title" => _}}} =
               request(:put, "/books/#{id}", %{"author" => "A"})

      assert {200, %{"title" => "Dune"}} = request(:get, "/books/#{id}")
    end

    test "404 for unknown id" do
      assert {404, _} = request(:put, "/books/999", @dune)
    end
  end

  describe "DELETE /books/:id" do
    test "deletes the book" do
      %{"id" => id} = create!(@dune)
      assert {204, nil} = request(:delete, "/books/#{id}")
      assert {404, _} = request(:get, "/books/#{id}")
      assert {404, _} = request(:delete, "/books/#{id}")
    end
  end

  test "unknown route returns JSON 404" do
    assert {404, %{"error" => "Not found"}} = request(:get, "/nope")
  end
end
