defmodule BookApi.BooksTest do
  use ExUnit.Case, async: false

  alias BookApi.{Books, DB}

  setup do
    {:ok, _} = DB.query("DELETE FROM books")
    :ok
  end

  @valid %{"title" => "Dune", "author" => "Frank Herbert", "year" => 1965, "isbn" => "9780441172719"}

  test "create stores and returns the book with an id" do
    assert {:ok, book} = Books.create(@valid)
    assert is_integer(book.id)
    assert %{title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441172719"} = book
  end

  test "create rejects missing title and author" do
    assert {:error, {:validation, errors}} = Books.create(%{"year" => 2000})
    assert errors == %{"title" => "is required", "author" => "is required"}
  end

  test "create rejects blank strings and bad year/isbn types" do
    attrs = %{"title" => "   ", "author" => "A", "year" => "1999", "isbn" => 123}
    assert {:error, {:validation, errors}} = Books.create(attrs)
    assert errors["title"] == "must not be blank"
    assert errors["year"] == "must be an integer between 0 and 9999"
    assert errors["isbn"] == "must be a string"
  end

  test "list filters by author case-insensitively" do
    {:ok, _} = Books.create(@valid)
    {:ok, _} = Books.create(%{"title" => "Emma", "author" => "Jane Austen"})

    assert {:ok, [book]} = Books.list(%{"author" => "frank herbert"})
    assert book.title == "Dune"
    assert {:ok, all} = Books.list()
    assert length(all) == 2
  end

  test "update replaces fields and returns the new state" do
    {:ok, book} = Books.create(@valid)
    assert {:ok, updated} = Books.update(book.id, %{"title" => "Dune Messiah", "author" => "Frank Herbert"})
    assert updated.title == "Dune Messiah"
    assert updated.year == nil
  end

  test "get, update and delete return not_found for unknown ids" do
    assert {:error, :not_found} = Books.get(999_999)
    assert {:error, :not_found} = Books.update(999_999, @valid)
    assert {:error, :not_found} = Books.delete(999_999)
  end

  test "delete removes the book" do
    {:ok, book} = Books.create(@valid)
    assert :ok = Books.delete(book.id)
    assert {:error, :not_found} = Books.get(book.id)
  end
end
