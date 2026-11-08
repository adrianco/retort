defmodule Books.RouterTest do
  use ExUnit.Case, async: false
  import Plug.Test
  import Plug.Conn
  alias Books.{Repo, Router}

  setup do
    Repo.delete_all(Books.Book)
    :ok
  end

  defp request(method, path, body \\ nil) do
    conn = conn(method, path, if(is_nil(body), do: "", else: Jason.encode!(body)))
    conn = if body, do: put_req_header(conn, "content-type", "application/json"), else: conn
    Router.call(conn, Router.init([]))
  end

  defp data(conn), do: Jason.decode!(conn.resp_body)

  test "health and complete book lifecycle" do
    assert data(request(:get, "/health")) == %{"status" => "ok"}

    created =
      request(:post, "/books", %{title: "Dune", author: "Frank Herbert", year: 1965, isbn: "123"})

    assert created.status == 201
    book = data(created)
    id = book["id"]
    assert book["title"] == "Dune"
    assert data(request(:get, "/books/#{id}")) == book
    updated = request(:put, "/books/#{id}", %{title: "Dune Messiah"})
    assert updated.status == 200
    assert data(updated)["author"] == "Frank Herbert"
    assert data(updated)["title"] == "Dune Messiah"
    assert request(:delete, "/books/#{id}").status == 204
    assert request(:get, "/books/#{id}").status == 404
  end

  test "list filters by exact author" do
    request(:post, "/books", %{title: "One", author: "A"})
    request(:post, "/books", %{title: "Two", author: "B"})
    assert length(data(request(:get, "/books"))) == 2
    assert [%{"title" => "One"}] = data(request(:get, "/books?author=A"))
  end

  test "validates required fields and types on create and update" do
    invalid = request(:post, "/books", %{title: "  ", year: "oops"})
    assert invalid.status == 422
    assert Map.keys(data(invalid)["errors"]) |> Enum.sort() == ["author", "title", "year"]
    book = data(request(:post, "/books", %{title: "One", author: "A"}))
    assert request(:put, "/books/#{book["id"]}", %{author: ""}).status == 422
    assert data(request(:get, "/books/#{book["id"]}"))["author"] == "A"
  end

  test "missing or invalid IDs and malformed JSON return errors" do
    assert request(:get, "/books/nope").status == 404
    assert request(:put, "/books/999", %{title: "X"}).status == 404
    assert request(:delete, "/books/999").status == 404

    bad =
      conn(:post, "/books", "{")
      |> put_req_header("content-type", "application/json")
      |> Router.call(Router.init([]))

    assert bad.status == 400
  end
end
