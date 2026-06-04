defmodule BookApi.BooksTest do
  use BookApi.DataCase

  alias BookApi.Books
  alias BookApi.Book

  describe "create_book/1" do
    test "creates a book with valid attributes" do
      attrs = %{"title" => "Dune", "author" => "Frank Herbert", "year" => 1965, "isbn" => "9780441013593"}
      assert {:ok, %Book{} = book} = Books.create_book(attrs)
      assert book.title == "Dune"
      assert book.author == "Frank Herbert"
      assert book.year == 1965
    end

    test "fails when title is missing" do
      assert {:error, changeset} = Books.create_book(%{"author" => "Someone"})
      refute changeset.valid?
      assert %{title: ["can't be blank"]} = errors_on(changeset)
    end

    test "fails when author is missing" do
      assert {:error, changeset} = Books.create_book(%{"title" => "A Book"})
      refute changeset.valid?
      assert %{author: ["can't be blank"]} = errors_on(changeset)
    end
  end

  describe "list_books/1" do
    test "lists all books and filters by author" do
      {:ok, _} = Books.create_book(%{"title" => "Book A", "author" => "Alice"})
      {:ok, _} = Books.create_book(%{"title" => "Book B", "author" => "Bob"})

      assert length(Books.list_books()) == 2
      assert [%Book{author: "Alice"}] = Books.list_books(author: "Alice")
    end
  end

  describe "update_book/2 and delete_book/1" do
    test "updates a book" do
      {:ok, book} = Books.create_book(%{"title" => "Old", "author" => "Author"})
      assert {:ok, updated} = Books.update_book(book, %{"title" => "New"})
      assert updated.title == "New"
    end

    test "deletes a book" do
      {:ok, book} = Books.create_book(%{"title" => "Temp", "author" => "Author"})
      assert {:ok, _} = Books.delete_book(book)
      assert Books.get_book(book.id) == nil
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
