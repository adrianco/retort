defmodule BookApiTest do
  use ExUnit.Case, async: false

  setup do
    path = Path.join(System.tmp_dir!(), "books-test-#{System.unique_integer([:positive])}.db")
    {:ok, _pid} = BookApi.Store.start_link(path)

    on_exit(fn ->
      if Process.whereis(BookApi.Store), do: GenServer.stop(BookApi.Store)
      File.rm(path)
    end)

    :ok
  end

  defp request(method, path, body \\ nil) do
    conn = Plug.Test.conn(method, path, body)
    BookApi.Router.call(conn, BookApi.Router.init([]))
  end

  test "health returns a JSON success response" do
    conn = request(:get, "/health")
    assert conn.status == 200
    assert Jason.decode!(conn.resp_body) == %{"status" => "ok"}
  end

  test "creates books and rejects missing required fields" do
    conn =
      request(
        :post,
        "/books",
        Jason.encode!(%{
          "title" => "Dune",
          "author" => "Frank Herbert",
          "year" => 1965,
          "isbn" => "123"
        })
      )

    assert conn.status == 201
    assert %{"id" => id, "title" => "Dune"} = Jason.decode!(conn.resp_body)

    invalid = request(:post, "/books", Jason.encode!(%{"title" => "No author"}))
    assert invalid.status == 400
    assert id > 0
  end

  test "lists with author filtering and gets, updates, and deletes a book" do
    {:ok, book} =
      BookApi.Store.create(%{
        "title" => "Dune",
        "author" => "Frank Herbert",
        "year" => 1965,
        "isbn" => nil
      })

    id = book["id"]

    assert [%{"id" => ^id}] =
             Jason.decode!(request(:get, "/books?author=Frank%20Herbert").resp_body)

    assert request(:get, "/books/#{id}").status == 200

    updated =
      request(
        :put,
        "/books/#{id}",
        Jason.encode!(%{"title" => "Dune Messiah", "author" => "Frank Herbert"})
      )

    assert updated.status == 200
    assert Jason.decode!(updated.resp_body)["title"] == "Dune Messiah"

    assert request(:delete, "/books/#{id}").status == 200
    assert request(:get, "/books/#{id}").status == 404
  end
end
