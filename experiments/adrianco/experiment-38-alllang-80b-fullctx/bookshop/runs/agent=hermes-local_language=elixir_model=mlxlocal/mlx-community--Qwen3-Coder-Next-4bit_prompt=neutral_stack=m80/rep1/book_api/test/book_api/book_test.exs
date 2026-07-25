defmodule BookApi.BookTest do
  use BookApi.DataCase, async: true

  alias BookApi.Book

  describe "changeset/2" do
    test "with valid data" do
      attrs = %{title: "Test Book", author: "Test Author", year: 2024, isbn: "1234567890"}
      changeset = Book.changeset(%Book{}, attrs)

      assert changeset.valid?
      assert changeset.changes == attrs
    end

    test "with missing required title" do
      attrs = %{author: "Test Author", year: 2024, isbn: "1234567890"}
      changeset = Book.changeset(%Book{}, attrs)

      refute changeset.valid?
      assert {:title, {"can't be blank", [_]}} in changeset.errors
    end

    test "with missing required author" do
      attrs = %{title: "Test Book", year: 2024, isbn: "1234567890"}
      changeset = Book.changeset(%Book{}, attrs)

      refute changeset.valid?
      assert {:author, {"can't be blank", [_]}} in changeset.errors
    end

    test "with invalid isbn length" do
      attrs = %{title: "Test Book", author: "Test Author", year: 2024, isbn: String.duplicate("1", 100)}
      changeset = Book.changeset(%Book{}, attrs)

      refute changeset.valid?
      assert {:isbn, {"should be at most 20 character(s)", [count: 100, max: 20, type: :string, length: :max]}} in changeset.errors
    end
  end
end
