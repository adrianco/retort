defmodule BookApi.Books do
  @moduledoc """
  Context module for managing books.
  """

  import Ecto.Query, warn: false

  alias BookApi.Repo
  alias BookApi.Book

  @doc "Lists all books, optionally filtered by author."
  def list_books(opts \\ []) do
    query = from(b in Book, order_by: [asc: b.id])

    query =
      case Keyword.get(opts, :author) do
        nil -> query
        "" -> query
        author -> from(b in query, where: b.author == ^author)
      end

    Repo.all(query)
  end

  @doc "Gets a single book. Returns nil if not found."
  def get_book(id), do: Repo.get(Book, id)

  @doc "Creates a book."
  def create_book(attrs) do
    %Book{}
    |> Book.changeset(attrs)
    |> Repo.insert()
  end

  @doc "Updates a book."
  def update_book(%Book{} = book, attrs) do
    book
    |> Book.changeset(attrs)
    |> Repo.update()
  end

  @doc "Deletes a book."
  def delete_book(%Book{} = book), do: Repo.delete(book)
end
