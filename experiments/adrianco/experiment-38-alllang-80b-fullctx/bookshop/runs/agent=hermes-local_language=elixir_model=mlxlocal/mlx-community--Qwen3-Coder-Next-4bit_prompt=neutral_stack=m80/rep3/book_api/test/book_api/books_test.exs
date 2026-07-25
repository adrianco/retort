defmodule BookAPI.BooksTest do
  use ExUnit.Case, async: true

  alias BookAPI.Books

  describe "list_books/1" do
    test "returns all books" do
      book = insert(:book, title: "Test Book", author: "Test Author")
      books = Books.list_books()
      assert length(books) == 1
      assert hd(books).title == "Test Book"
    end

    test "filters books by author" do
      insert(:book, title: "Book 1", author: "Author A")
      insert(:book, title: "Book 2", author: "Author B")
      insert(:book, title: "Book 3", author: "Author A")

      books = Books.list_books(author: "Author A")
      assert length(books) == 2
      Enum.each(books, fn b -> assert b.author == "Author A" end)
    end
  end

  describe "get_book!/1" do
    test "returns the book with given id" do
      book = insert(:book, title: "Test Book", author: "Test Author")
      retrieved_book = Books.get_book!(book.id)
      assert retrieved_book.title == "Test Book"
    end

    test "raises if book not found" do
      assert_raise Ecto.NoResultsError, fn ->
        Books.get_book!(999_999)
      end
    end
  end

  describe "create_book/1" do
    test "creates a book with valid data" do
      attrs = %{title: "New Book", author: "New Author", year: 2024, isbn: "1234567890"}
      {:ok, %Book{} = book} = Books.create_book(attrs)
      assert book.title == "New Book"
      assert book.author == "New Author"
      assert book.year == 2024
      assert book.isbn == "1234567890"
    end

    test "returns error with invalid data (missing required fields)" do
      attrs = %{year: 2024, isbn: "1234567890"}
      {:error, %Ecto.Changeset{}} = Books.create_book(attrs)
    end

    test "validates title is required" do
      attrs = %{author: "Some Author", year: 2024}
      {:error, %Ecto.Changeset{errors: errors}} = Books.create_book(attrs)
      assert {:title, {"can't be blank", [_]}} in errors
    end

    test "validates author is required" do
      attrs = %{title: "Some Title", year: 2024}
      {:error, %Ecto.Changeset{errors: errors}} = Books.create_book(attrs)
      assert {:author, {"can't be blank", [_]}} in errors
    end
  end

  describe "update_book/2" do
    test "updates a book with valid data" do
      book = insert(:book, title: "Old Title", author: "Old Author")
      attrs = %{title: "New Title", author: "New Author"}
      {:ok, %Book{} = updated_book} = Books.update_book(book, attrs)
      assert updated_book.title == "New Title"
      assert updated_book.author == "New Author"
    end

    test "returns error with invalid data" do
      book = insert(:book, title: "Old Title", author: "Old Author")
      attrs = %{year: 2024}
      {:error, %Ecto.Changeset{}} = Books.update_book(book, attrs)
    end
  end

  describe "delete_book/1" do
    test "deletes a book" do
      book = insert(:book, title: "To Delete", author: "Delete Author")
      {:ok, %Book{} = deleted_book} = Books.delete_book(book)
      assert deleted_book.title == "To Delete"

      assert Books.list_books() == []
    end
  end

  defp insert(:book, attrs \\ %{}) do
    {:ok, book} =
      attrs
      |> Map.put_new(:title, "Test Book")
      |> Map.put_new(:author, "Test Author")
      |> BookAPI.Books.create_book()

    book
  end
end
