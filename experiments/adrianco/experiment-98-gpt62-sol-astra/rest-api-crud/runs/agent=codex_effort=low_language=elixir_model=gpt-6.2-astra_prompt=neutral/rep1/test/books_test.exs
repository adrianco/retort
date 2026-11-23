defmodule BooksTest do
  use ExUnit.Case
  import Plug.Test

  defp request(method, path, body \\ nil) do
    conn(method, path, body) |> Books.Router.call(Books.Router.init([]))
  end

  defp create(author) do
    request(
      :post,
      "/books",
      JSON.encode!(%{title: "Home", author: author, year: 2008, isbn: "0001"})
    )
  end

  test "create, retrieve, replace and delete a book" do
    created = create("Robinson")
    assert created.status == 201
    [path] = Plug.Conn.get_resp_header(created, "location")
    book = JSON.decode!(created.resp_body)
    assert book["isbn"] == "0001"
    assert book["year"] == 2008
    assert request(:get, path).resp_body |> JSON.decode!() == book
    updated = request(:put, path, ~s({"title":"Gilead","author":"Robinson"}))
    assert updated.status == 200

    assert JSON.decode!(request(:get, path).resp_body) == %{
             book
             | "title" => "Gilead",
               "year" => nil,
               "isbn" => nil
           }

    assert request(:delete, path).status == 204
    assert request(:get, path).status == 404
    assert request(:delete, path).status == 404
  end

  test "list and filter by exact author" do
    a = JSON.decode!(create("Alice Smith").resp_body)
    b = JSON.decode!(create("Bob").resp_body)
    books = JSON.decode!(request(:get, "/books").resp_body)
    assert a in books and b in books
    assert JSON.decode!(request(:get, "/books?author=Alice%20Smith").resp_body) == [a]
  end

  test "invalid writes return JSON errors and preserve the stored book" do
    for fields <- [%{title: "Title"}, %{author: "Author"}, %{title: " ", author: "Author"}] do
      assert request(:post, "/books", JSON.encode!(fields)).status == 422
    end

    assert request(:post, "/books", "{").status == 400
    created = create("Toni Morrison")
    [path] = Plug.Conn.get_resp_header(created, "location")
    assert request(:put, path, "{}").status == 422
    assert request(:get, path).resp_body == created.resp_body
  end

  test "health check" do
    response = request(:get, "/health")
    assert response.status == 200
    assert JSON.decode!(response.resp_body) == %{"status" => "ok"}
  end
end
