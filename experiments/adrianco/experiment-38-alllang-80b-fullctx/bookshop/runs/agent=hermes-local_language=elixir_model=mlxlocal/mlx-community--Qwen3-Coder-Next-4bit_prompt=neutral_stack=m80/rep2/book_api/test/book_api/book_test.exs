defmodule BookApi.BookTest do
  use BookApi.DataCase, async: true

  alias BookApi.Book

  describe "changeset/2" do
    test "with valid data" do
      attrs = %{title: "Test Book", author: "Test Author", year: 2024, isbn: "1234567890"}
      changeset = Book.changeset(%Book{}, attrs)
      assert changeset.valid?
    end

    test "with missing title" do
      attrs = %{author: "Test Author", year: 2024, isbn: "1234567890"}
      changeset = Book.changeset(%Book{}, attrs)
      refute changeset.valid?
      assert {:title, _} in changeset.errors
    end

    test "with missing author" do
      attrs = %{title: "Test Book", year: 2024, isbn: "1234567890"}
      changeset = Book.changeset(%Book{}, attrs)
      refute changeset.valid?
      assert {:author, _} in changeset.errors
    end

    test "with invalid ISBN format" do
      attrs = %{title: "Test Book", author: "Test Author", year: 2024, isbn: "invalid-isbn!@#"}
      changeset = Book.changeset(%Book{}, attrs)
      refute changeset.valid?
      assert {:isbn, _} in changeset.errors
    end

    test "with title too long" do
      attrs = %{title: String.duplicate("a", 300), author: "Test Author", year: 2024, isbn: "1234567890"}
      changeset = Book.changeset(%Book{}, attrs)
      refute changeset.valid?
      assert {:title, _} in changeset.errors
    end

    test "with author too long" do
      attrs = %{title: "Test Book", author: String.duplicate("a", 300), year: 2024, isbn: "1234567890"}
      changeset = Book.changeset(%Book{}, attrs)
      refute changeset.valid?
      assert {:author, _} in changeset.errors
    end
  end
end
