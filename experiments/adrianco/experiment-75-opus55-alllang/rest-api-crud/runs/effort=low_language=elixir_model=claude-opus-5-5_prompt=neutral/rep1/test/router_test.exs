defmodule Books.RouterTest do
  use ExUnit.Case
  import Plug.Test
  import Plug.Conn

  setup do
    Books.Repo.reset()
    :ok
  end

  defp call(method, path, body \\ nil) do
    conn =
      if body,
        do: conn(method, path, Jason.encode!(body)) |> put_req_header("content-type", "application/json"),
        else: conn(method, path)

    conn = Books.Router.call(conn, Books.Router.init([]))
    {conn.status, if(conn.resp_body == "", do: nil, else: Jason.decode!(conn.resp_body))}
  end

  @book %{"title" => "Dune", "author" => "Frank Herbert", "year" => 1965, "isbn" => "9780441013593"}

  test "health check" do
    assert {200, %{"status" => "ok"}} = call(:get, "/health")
  end

  test "full CRUD lifecycle" do
    {201, %{"id" => id} = created} = call(:post, "/books", @book)
    assert created["title"] == "Dune"
    assert {200, ^created} = call(:get, "/books/#{id}")
    assert {200, [^created]} = call(:get, "/books")

    {200, updated} = call(:put, "/books/#{id}", %{@book | "title" => "Dune Messiah", "year" => 1969})
    assert updated["title"] == "Dune Messiah" and updated["year"] == 1969

    assert {204, nil} = call(:delete, "/books/#{id}")
    assert {404, _} = call(:get, "/books/#{id}")
    assert {404, _} = call(:delete, "/books/#{id}")
  end

  test "validation requires title and author" do
    assert {422, %{"errors" => errs}} = call(:post, "/books", %{"year" => "x"})
    assert Map.keys(errs) |> Enum.sort() == ["author", "title", "year"]
    assert {422, _} = call(:post, "/books", %{"title" => " ", "author" => "A"})

    {201, %{"id" => id}} = call(:post, "/books", @book)
    assert {422, _} = call(:put, "/books/#{id}", %{"title" => "only"})
  end

  test "filter by author" do
    call(:post, "/books", @book)
    call(:post, "/books", %{"title" => "Emma", "author" => "Jane Austen"})
    assert {200, [%{"title" => "Emma"}]} = call(:get, "/books?author=Jane%20Austen")
    assert {200, list} = call(:get, "/books")
    assert length(list) == 2
  end

  test "unknown or invalid ids return 404" do
    assert {404, _} = call(:get, "/books/999")
    assert {404, _} = call(:get, "/books/abc")
    assert {404, _} = call(:put, "/books/999", @book)
  end
end
