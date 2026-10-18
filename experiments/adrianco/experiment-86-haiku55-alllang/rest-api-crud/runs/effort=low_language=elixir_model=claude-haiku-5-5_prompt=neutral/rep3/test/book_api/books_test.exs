defmodule BookApi.BooksTest do
  use ExUnit.Case, async: false

  alias BookApi.{Books, Repo, Book}

  setup do
    Repo.delete_all(Book)
    :ok
  end

  @valid %{
    "title" => "Dune",
    "author" => "Frank Herbert",
    "year" => 1965,
    "isbn" => "9780441013593"
  }

  test "create_book/1 persists a valid book" do
    assert {:ok, %Book{id: id, title: "Dune"}} = Books.create_book(@valid)
    assert is_integer(id)
  end

  test "create_book/1 requires title and author" do
    assert {:error, cs} = Books.create_book(%{"year" => 1965})
    assert %{title: ["is required"], author: ["is required"]} = errors_on(cs)
  end

  test "list_books/1 filters by author" do
    {:ok, _} = Books.create_book(@valid)
    {:ok, _} = Books.create_book(%{"title" => "Emma", "author" => "Jane Austen"})

    assert [%Book{author: "Frank Herbert"}] = Books.list_books(%{"author" => "Frank Herbert"})
    assert length(Books.list_books(%{})) == 2
  end

  test "update_book/2 changes fields and keeps unspecified ones" do
    {:ok, book} = Books.create_book(@valid)

    assert {:ok, %Book{title: "Dune Messiah", author: "Frank Herbert"}} =
             Books.update_book(book, %{"title" => "Dune Messiah"})
  end

  test "delete_book/1 removes the book" do
    {:ok, book} = Books.create_book(@valid)
    assert {:ok, _} = Books.delete_book(book)
    assert Books.get_book(book.id) == nil
  end

  defp errors_on(changeset) do
    Ecto.Changeset.traverse_errors(changeset, fn {msg, opts} ->
      Regex.replace(~r"%{(\w+)}", msg, fn _, key ->
        opts |> Keyword.get(String.to_existing_atom(key), key) |> to_string()
      end)
    end)
  end
end
