defmodule BooksApi.BooksTest do
  use BooksApi.DataCase, async: false

  describe "create_book/1" do
    test "creates a book with valid attributes" do
      assert {:ok, book} =
               Books.create_book(%{
                 "title" => "The Mythical Man-Month",
                 "author" => "Fred Brooks",
                 "year" => 1975,
                 "isbn" => "978-0201835953"
               })

      assert book.id
      assert book.title == "The Mythical Man-Month"
      assert book.author == "Fred Brooks"
      assert book.year == 1975
    end

    test "requires title and author" do
      assert {:error, changeset} = Books.create_book(%{"year" => 2000})
      errors = Keyword.keys(changeset.errors)
      assert :title in errors
      assert :author in errors
    end

    test "rejects an out-of-range year" do
      assert {:error, changeset} =
               Books.create_book(%{"title" => "T", "author" => "A", "year" => -5})

      assert Keyword.has_key?(changeset.errors, :year)
    end
  end

  describe "list_books/1" do
    test "lists all books and filters by author" do
      {:ok, _} = Books.create_book(%{"title" => "Book One", "author" => "Alice"})
      {:ok, _} = Books.create_book(%{"title" => "Book Two", "author" => "Bob"})
      {:ok, _} = Books.create_book(%{"title" => "Book Three", "author" => "Alice"})

      assert length(Books.list_books()) == 3

      by_alice = Books.list_books(%{author: "Alice"})
      assert length(by_alice) == 2
      assert Enum.all?(by_alice, &(&1.author == "Alice"))
    end
  end

  describe "update_book/2" do
    test "updates fields and validates" do
      {:ok, book} = Books.create_book(%{"title" => "Old", "author" => "A"})

      assert {:ok, updated} = Books.update_book(book, %{"title" => "New"})
      assert updated.title == "New"

      assert {:error, changeset} = Books.update_book(book, %{"title" => ""})
      assert Keyword.has_key?(changeset.errors, :title)
    end
  end

  describe "delete_book/1" do
    test "deletes a book" do
      {:ok, book} = Books.create_book(%{"title" => "Gone", "author" => "A"})
      assert {:ok, _} = Books.delete_book(book)
      assert Books.get_book(book.id) == nil
    end
  end
end
