defmodule BookApi.BooksTest do
  use BookApi.ApiCase

  alias BookApi.Books.Book

  describe "create_book/1" do
    test "trims surrounding whitespace on text fields" do
      {:ok, book} = Books.create_book(%{"title" => "  Dune  ", "author" => " Herbert "})

      assert book.title == "Dune"
      assert book.author == "Herbert"
    end

    test "normalises a blank isbn to nil so blanks don't collide" do
      {:ok, first} = Books.create_book(%{"title" => "A", "author" => "X", "isbn" => ""})
      {:ok, second} = Books.create_book(%{"title" => "B", "author" => "Y", "isbn" => "  "})

      assert first.isbn == nil
      assert second.isbn == nil
    end

    test "rejects a duplicate isbn" do
      attrs = %{"title" => "A", "author" => "X", "isbn" => "0306406152"}
      {:ok, _} = Books.create_book(attrs)

      assert {:error, changeset} = Books.create_book(%{attrs | "title" => "B"})
      assert errors_on(changeset)[:isbn] == ["has already been taken"]
    end

    test "accepts an ISBN-10 ending in the X check digit" do
      assert {:ok, book} =
               Books.create_book(%{"title" => "A", "author" => "X", "isbn" => "155860832X"})

      assert book.isbn == "155860832X"
    end

    test "rejects an out-of-range year" do
      assert {:error, changeset} =
               Books.create_book(%{"title" => "A", "author" => "X", "year" => -5})

      assert errors_on(changeset)[:year] == ["must be greater than 0"]
    end
  end

  describe "list_books/1" do
    test "orders newest first" do
      insert_book(%{"title" => "Older"})
      insert_book(%{"title" => "Newer"})

      assert ["Newer", "Older"] = Enum.map(Books.list_books(), & &1.title)
    end

    test "ignores a nil author filter" do
      insert_book()

      assert length(Books.list_books(author: nil)) == 1
    end
  end

  describe "get_book/1" do
    test "accepts integer and string ids and returns nil otherwise" do
      book = insert_book()

      assert Books.get_book(book.id).id == book.id
      assert Books.get_book(to_string(book.id)).id == book.id
      assert Books.get_book("#{book.id}-oops") == nil
      assert Books.get_book(nil) == nil
    end
  end

  describe "update_book/2 and delete_book/1" do
    test "update applies validation" do
      book = insert_book()

      assert {:error, changeset} = Books.update_book(book, %{"author" => nil})
      assert errors_on(changeset)[:author] == ["can't be blank"]
    end

    test "delete removes the row" do
      book = insert_book()

      assert {:ok, _} = Books.delete_book(book)
      assert Repo.aggregate(Book, :count) == 0
    end
  end

  defp errors_on(changeset) do
    Ecto.Changeset.traverse_errors(changeset, fn {msg, opts} ->
      Regex.replace(~r"%{(\w+)}", msg, fn _, key ->
        opts |> Keyword.get(String.to_existing_atom(key), key) |> to_string()
      end)
    end)
  end
end
