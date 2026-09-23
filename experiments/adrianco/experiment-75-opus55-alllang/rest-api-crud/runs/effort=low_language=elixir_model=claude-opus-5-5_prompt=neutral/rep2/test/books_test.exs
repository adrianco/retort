defmodule BooksTest do
  use ExUnit.Case
  import Plug.Test
  import Plug.Conn

  setup do
    Books.Repo.reset()
    :ok
  end

  defp req(method, path, body \\ nil) do
    conn =
      if body,
        do: conn(method, path, Jason.encode!(body)) |> put_req_header("content-type", "application/json"),
        else: conn(method, path)

    conn = Books.Router.call(conn, Books.Router.init([]))
    {conn.status, if(conn.resp_body == "", do: nil, else: Jason.decode!(conn.resp_body))}
  end

  @book %{"title" => "Dune", "author" => "Frank Herbert", "year" => 1965, "isbn" => "123"}

  test "health" do
    assert {200, %{"status" => "ok"}} = req(:get, "/health")
  end

  test "create and fetch a book" do
    {201, %{"id" => id} = b} = req(:post, "/books", @book)
    assert b["title"] == "Dune"
    assert {200, ^b} = req(:get, "/books/#{id}")
  end

  test "validation requires title and author" do
    assert {422, %{"errors" => errs}} = req(:post, "/books", %{"year" => "x"})
    assert "title is required" in errs and "author is required" in errs
    assert "year must be an integer" in errs
  end

  test "list with author filter" do
    req(:post, "/books", @book)
    req(:post, "/books", %{@book | "title" => "Emma", "author" => "Jane Austen"})
    assert {200, [_, _]} = req(:get, "/books")
    assert {200, [%{"title" => "Emma"}]} = req(:get, "/books?author=Jane%20Austen")
  end

  test "update and delete" do
    {201, %{"id" => id}} = req(:post, "/books", @book)
    assert {200, %{"title" => "Dune Messiah"}} = req(:put, "/books/#{id}", %{@book | "title" => "Dune Messiah"})
    assert {422, _} = req(:put, "/books/#{id}", %{"title" => ""})
    assert {204, nil} = req(:delete, "/books/#{id}")
    assert {404, _} = req(:get, "/books/#{id}")
    assert {404, _} = req(:delete, "/books/#{id}")
    assert {404, _} = req(:put, "/books/#{id}", @book)
  end
end
