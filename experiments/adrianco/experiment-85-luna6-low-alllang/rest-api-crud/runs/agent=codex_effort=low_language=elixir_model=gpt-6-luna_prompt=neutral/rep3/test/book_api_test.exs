defmodule BookApiTest do
  use ExUnit.Case, async: false

  setup do
    path = Path.join(System.tmp_dir!(), "books-test-#{System.unique_integer([:positive])}.sqlite3")
    System.put_env("BOOKS_DB", path)
    BookApi.Store.init()
    on_exit(fn -> File.rm(path); System.delete_env("BOOKS_DB") end)
    :ok
  end

  test "creates and retrieves a book" do
    book = BookApi.Store.create(%{"title" => "Dune", "author" => "Frank Herbert", "year" => 1965, "isbn" => "123"})
    assert book["title"] == "Dune"
    assert BookApi.Store.get(book["id"])["author"] == "Frank Herbert"
  end

  test "filters books by author" do
    BookApi.Store.create(%{"title" => "Dune", "author" => "Frank Herbert"})
    BookApi.Store.create(%{"title" => "Foundation", "author" => "Isaac Asimov"})
    assert Enum.map(BookApi.Store.list("frank herbert"), & &1["title"]) == ["Dune"]
  end

  test "updates and deletes a book" do
    book = BookApi.Store.create(%{"title" => "Old", "author" => "Author"})
    assert BookApi.Store.update(book["id"], %{"title" => "New", "author" => "Author"})["title"] == "New"
    assert BookApi.Store.delete(book["id"])
    assert BookApi.Store.get(book["id"]) == nil
  end

  test "validates required fields" do
    assert BookApi.Server.validate(%{"title" => "", "author" => "A"}) == {:error, :validation}
  end
end
