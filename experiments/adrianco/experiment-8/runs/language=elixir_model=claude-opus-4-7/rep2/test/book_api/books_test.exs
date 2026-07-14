defmodule BookApi.BooksTest do
  use BookApi.DataCase, async: false

  alias BookApi.Books

  @valid_attrs %{"title" => "Dune", "author" => "Frank Herbert", "year" => 1965, "isbn" => "9780441172719"}

  describe "create_book/1" do
    test "creates a book with valid attributes" do
      assert {:ok, book} = Books.create_book(@valid_attrs)
      assert book.title == "Dune"
      assert book.author == "Frank Herbert"
      assert book.year == 1965
      assert book.isbn == "9780441172719"
      assert is_integer(book.id)
    end

    test "returns an error when title is missing" do
      assert {:error, changeset} = Books.create_book(%{"author" => "Someone"})
      refute changeset.valid?
      assert %{title: ["can't be blank"]} = errors_on(changeset)
    end

    test "returns an error when author is missing" do
      assert {:error, changeset} = Books.create_book(%{"title" => "Untitled"})
      refute changeset.valid?
      assert %{author: ["can't be blank"]} = errors_on(changeset)
    end
  end

  describe "list_books/1" do
    test "filters by author" do
      {:ok, _} = Books.create_book(@valid_attrs)
      {:ok, _} = Books.create_book(%{"title" => "Foundation", "author" => "Isaac Asimov"})

      results = Books.list_books(%{"author" => "Isaac Asimov"})
      assert length(results) == 1
      assert hd(results).author == "Isaac Asimov"
    end

    test "returns all books when no filter provided" do
      {:ok, _} = Books.create_book(@valid_attrs)
      {:ok, _} = Books.create_book(%{"title" => "Foundation", "author" => "Isaac Asimov"})

      assert length(Books.list_books()) == 2
    end
  end

  describe "update_book/2 and delete_book/1" do
    test "updates a book's fields" do
      {:ok, book} = Books.create_book(@valid_attrs)
      assert {:ok, updated} = Books.update_book(book, %{"title" => "Dune (Revised)"})
      assert updated.title == "Dune (Revised)"
    end

    test "deletes a book" do
      {:ok, book} = Books.create_book(@valid_attrs)
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
