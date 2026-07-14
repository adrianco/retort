defmodule BookApi.BooksTest do
  use BookApi.DataCase, async: true

  alias BookApi.Books

  describe "create_book/1" do
    test "creates a book with valid attributes" do
      assert {:ok, book} =
               Books.create_book(%{
                 "title" => "Dune",
                 "author" => "Frank Herbert",
                 "year" => 1965,
                 "isbn" => "978-0441013593"
               })

      assert book.title == "Dune"
      assert book.author == "Frank Herbert"
      assert book.year == 1965
    end

    test "requires title and author" do
      assert {:error, changeset} = Books.create_book(%{"year" => 2000})
      errors = errors_on(changeset)
      assert "can't be blank" in errors.title
      assert "can't be blank" in errors.author
    end
  end

  describe "list_books/1" do
    test "filters by author" do
      {:ok, _} = Books.create_book(%{"title" => "A", "author" => "Alice"})
      {:ok, _} = Books.create_book(%{"title" => "B", "author" => "Bob"})

      assert [book] = Books.list_books(author: "Alice")
      assert book.author == "Alice"
    end
  end

  describe "update_book/2 and delete_book/1" do
    test "updates and deletes a book" do
      {:ok, book} = Books.create_book(%{"title" => "Old", "author" => "Author"})

      assert {:ok, updated} = Books.update_book(book, %{"title" => "New"})
      assert updated.title == "New"

      assert {:ok, _} = Books.delete_book(updated)
      assert Books.get_book(updated.id) == nil
    end
  end

  defp errors_on(changeset) do
    Ecto.Changeset.traverse_errors(changeset, fn {msg, opts} ->
      Enum.reduce(opts, msg, fn {key, value}, acc ->
        String.replace(acc, "%{#{key}}", to_string(value))
      end)
    end)
  end
end
