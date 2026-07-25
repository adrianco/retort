defmodule BooksApi.DataCase do
  @moduledoc """
  Test case template that wipes the books table before each test.

  Tests run against a dedicated SQLite test database file, so they must
  not run async.
  """

  use ExUnit.CaseTemplate

  using do
    quote do
      alias BooksApi.{Book, Books, Repo}
    end
  end

  setup do
    BooksApi.Repo.delete_all(BooksApi.Book)
    :ok
  end
end
