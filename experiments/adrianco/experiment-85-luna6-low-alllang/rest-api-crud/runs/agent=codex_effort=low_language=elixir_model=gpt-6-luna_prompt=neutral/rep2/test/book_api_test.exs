defmodule BookApiTest do
  use ExUnit.Case, async: false

  test "health check returns JSON success" do
    assert {200, body} = BookApi.Router.dispatch("GET", "/health", "", %{})
    assert {:ok, %{"status" => "ok"}} = BookApi.JSON.decode(body)
  end

  test "creates, fetches, updates, filters, and deletes books" do
    author = "Author #{System.unique_integer([:positive])}"

    payload =
      BookApi.JSON.encode(%{
        "title" => "First",
        "author" => author,
        "year" => 2024,
        "isbn" => "123"
      })

    assert {201, body} = BookApi.Router.dispatch("POST", "/books", payload, %{})
    assert {:ok, book} = BookApi.JSON.decode(body)
    id = book["id"]
    assert book["title"] == "First"

    assert {200, fetched} = BookApi.Router.dispatch("GET", "/books/#{id}", "", %{})
    assert {:ok, %{"id" => ^id}} = BookApi.JSON.decode(fetched)
    assert {200, list} = BookApi.Router.dispatch("GET", "/books", "", %{"author" => author})
    assert {:ok, [%{"id" => ^id}]} = BookApi.JSON.decode(list)

    updated = BookApi.JSON.encode(%{"title" => "Revised", "author" => author})
    assert {200, response} = BookApi.Router.dispatch("PUT", "/books/#{id}", updated, %{})
    assert {:ok, %{"title" => "Revised"}} = BookApi.JSON.decode(response)

    assert {204, ""} = BookApi.Router.dispatch("DELETE", "/books/#{id}", "", %{})
    assert {404, _} = BookApi.Router.dispatch("GET", "/books/#{id}", "", %{})
  end

  test "requires title and author and rejects malformed JSON" do
    assert {422, body} =
             BookApi.Router.dispatch("POST", "/books", ~s({"title":"Only title"}), %{})

    assert {:ok, %{"error" => _}} = BookApi.JSON.decode(body)
    assert {400, _} = BookApi.Router.dispatch("POST", "/books", "{broken", %{})
  end

  test "missing book returns 404" do
    assert {404, _} = BookApi.Router.dispatch("GET", "/books/99999999", "", %{})
  end
end
