defmodule BookApiTest do
  use ExUnit.Case, async: false

  setup do
    path = Path.join(System.tmp_dir!(), "book_api_test_#{System.unique_integer([:positive])}.db")
    Application.put_env(:book_api, :database_path, path)
    BookApi.Store.setup(path)
    on_exit(fn -> File.rm(path) end)
    :ok
  end

  test "creates and fetches a book" do
    body = ~s({"title":"Kindred","author":"Octavia Butler","year":1979,"isbn":"9780807083697"})
    assert {201, created} = BookApi.Router.route("POST", "/books", %{}, body)
    assert created["title"] == "Kindred"
    assert {200, fetched} = BookApi.Router.route("GET", "/books/#{created["id"]}", %{}, "")
    assert fetched["author"] == "Octavia Butler"
  end

  test "lists books filtered by author" do
    BookApi.Router.route("POST", "/books", %{}, ~s({"title":"Parable","author":"Octavia Butler"}))
    BookApi.Router.route("POST", "/books", %{}, ~s({"title":"Dune","author":"Frank Herbert"}))
    assert {200, [%{"title" => "Parable"}]} = BookApi.Router.route("GET", "/books", %{"author" => "Octavia Butler"}, "")
  end

  test "rejects books without required fields and supports health checks" do
    assert {422, %{error: "title is required"}} = BookApi.Router.route("POST", "/books", %{}, ~s({"author":"Ursula Le Guin"}))
    assert {200, %{status: "ok"}} = BookApi.Router.route("GET", "/health", %{}, "")
  end

  test "updates and deletes a book" do
    {201, created} = BookApi.Router.route("POST", "/books", %{}, ~s({"title":"Earthsea","author":"Ursula Le Guin"}))
    assert {200, %{"year" => 1968}} = BookApi.Router.route("PUT", "/books/#{created["id"]}", %{}, ~s({"title":"A Wizard of Earthsea","author":"Ursula Le Guin","year":1968}))
    assert {204, nil} = BookApi.Router.route("DELETE", "/books/#{created["id"]}", %{}, "")
    assert {404, _} = BookApi.Router.route("GET", "/books/#{created["id"]}", %{}, "")
  end
end
