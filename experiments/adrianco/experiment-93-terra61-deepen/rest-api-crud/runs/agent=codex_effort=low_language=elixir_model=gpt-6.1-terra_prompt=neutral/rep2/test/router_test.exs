defmodule BookCollection.RouterTest do
  use ExUnit.Case, async: false
  import Plug.Test
  import Plug.Conn
  alias BookCollection.{Repo, Router, Book}

  setup do
    Repo.delete_all(Book)
    :ok
  end

  defp request(method, path, body \\ nil) do
    conn(method, path, if(body, do: Jason.encode!(body), else: ""))
    |> put_req_header("content-type", "application/json")
    |> Router.call(Router.init([]))
  end

  defp decoded(conn), do: Jason.decode!(conn.resp_body)

  test "health check" do
    response = request(:get, "/health")
    assert response.status == 200
    assert decoded(response) == %{"status" => "ok"}
  end

  test "create, fetch, update and delete a book" do
    created = request(:post, "/books", %{title: "Dune", author: "Herbert", year: 1965, isbn: "123"})
    assert created.status == 201
    book = decoded(created)
    assert book["title"] == "Dune"
    id = book["id"]
    assert decoded(request(:get, "/books/#{id}")) == book
    updated = request(:put, "/books/#{id}", %{title: "Dune Messiah"})
    assert updated.status == 200
    assert decoded(updated)["title"] == "Dune Messiah"
    assert decoded(updated)["author"] == "Herbert"
    assert request(:delete, "/books/#{id}").status == 204
    assert request(:get, "/books/#{id}").status == 404
  end

  test "lists books and filters by author" do
    request(:post, "/books", %{title: "One", author: "A"})
    request(:post, "/books", %{title: "Two", author: "B"})
    assert length(decoded(request(:get, "/books"))) == 2
    assert [%{"title" => "One"}] = decoded(request(:get, "/books?author=A"))
  end

  test "malformed JSON returns a JSON error" do
    response = conn(:post, "/books", "{") |> put_req_header("content-type", "application/json") |> Router.call(Router.init([]))
    assert response.status == 400
    assert decoded(response) == %{"error" => "Invalid JSON"}
  end

  test "validates required fields and types" do
    response = request(:post, "/books", %{title: " ", year: "bad"})
    assert response.status == 422
    assert Map.keys(decoded(response)["errors"]) |> Enum.sort() == ["author", "title", "year"]
    assert request(:get, "/books/not-an-id").status == 404
  end
end
