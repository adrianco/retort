defmodule BookCollection.RouterTest do
  use ExUnit.Case, async: false
  import Plug.Conn
  import Plug.Test

  alias BookCollection.Router

  setup do
    {:ok, books} = BookCollection.Store.list(nil)
    Enum.each(books, fn book -> {:ok, _} = BookCollection.Store.delete(book.id) end)
    :ok
  end

  test "creates, lists, and retrieves a book" do
    attrs = %{title: "  Kindred ", author: "Octavia E. Butler", year: 1979, isbn: "9780807083697"}
    created = request(:post, "/books", attrs)
    assert created.status == 201
    book = decode(created)

    assert %{
             "id" => id,
             "title" => "Kindred",
             "author" => "Octavia E. Butler",
             "year" => 1979,
             "isbn" => "9780807083697"
           } = book

    assert get_resp_header(created, "location") == ["/books/#{id}"]

    fetched = request(:get, "/books/#{id}")
    assert fetched.status == 200
    assert decode(fetched) == book

    listed = request(:get, "/books")
    assert listed.status == 200
    assert decode(listed) == [book]
  end

  test "filters by exact author and treats SQL characters as data" do
    author = "O'Neil"
    expected = request(:post, "/books", %{title: "First", author: author}) |> decode()
    assert request(:post, "/books", %{title: "Second", author: "Other"}).status == 201

    filtered = request(:get, "/books?author=#{URI.encode_www_form(author)}")
    assert filtered.status == 200
    assert decode(filtered) == [expected]
    assert decode(request(:get, "/books?author=#{URI.encode_www_form("' OR 1=1 --")}")) == []
  end

  test "replaces a book and deletes it" do
    %{"id" => id} =
      request(:post, "/books", %{title: "Old", author: "Author", year: 2000}) |> decode()

    path = "/books/#{id}"
    updated = request(:put, path, %{title: "New", author: "New author", isbn: "001"})
    assert updated.status == 200

    assert decode(updated) == %{
             "id" => id,
             "title" => "New",
             "author" => "New author",
             "year" => nil,
             "isbn" => "001"
           }

    assert decode(request(:get, path)) == decode(updated)

    deleted = request(:delete, path)
    assert deleted.status == 204
    assert deleted.resp_body == ""
    assert request(:get, path).status == 404
    assert request(:delete, path).status == 404
    assert request(:put, path, %{title: "New", author: "Author"}).status == 404
    assert decode(request(:get, "/books")) == []
  end

  test "validates writes and rejects malformed request bodies" do
    invalid = request(:post, "/books", %{title: " ", year: "2000", isbn: 123})
    assert invalid.status == 422
    assert Enum.sort(Map.keys(decode(invalid)["errors"])) == ~w(author isbn title year)
    assert request(:post, "/books", "{").status == 400
    assert request(:post, "/books", "[]").status == 400
    assert request(:get, "/books/invalid").status == 400

    %{"id" => id} = request(:post, "/books", %{title: "Book", author: "Author"}) |> decode()
    assert request(:put, "/books/#{id}", %{title: "New"}).status == 422
    assert decode(request(:get, "/books/#{id}"))["title"] == "Book"
  end

  test "reports health and returns JSON for unknown routes" do
    health = request(:get, "/health")
    assert health.status == 200
    assert decode(health) == %{"status" => "ok"}
    assert ["application/json" <> _] = get_resp_header(health, "content-type")
    assert request(:get, "/unknown").status == 404
  end

  defp request(method, path, body \\ "") do
    body = if is_map(body), do: JSON.encode!(body), else: body

    method
    |> conn(path, body)
    |> put_req_header("content-type", "application/json")
    |> Router.call(Router.init([]))
  end

  defp decode(conn), do: JSON.decode!(conn.resp_body)
end
