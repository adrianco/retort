defmodule BookApi.Books do
  @moduledoc """
  The Books context: the data-access boundary for the book collection.
  """
  import Ecto.Query, warn: false

  alias BookApi.Repo
  alias BookApi.Book

  @doc """
  Returns the list of books, optionally filtered by author (case-insensitive).
  """
  def list_books(opts \\ []) do
    query = from(b in Book, order_by: [asc: b.id])

    query =
      case Keyword.get(opts, :author) do
        nil -> query
        "" -> query
        author -> from(b in query, where: like(fragment("lower(?)", b.author), ^"%#{String.downcase(author)}%"))
      end

    Repo.all(query)
  end

  @doc "Fetches a single book. Returns `nil` when not found."
  def get_book(id), do: Repo.get(Book, id)

  @doc "Creates a book from the given attributes."
  def create_book(attrs) do
    %Book{}
    |> Book.changeset(attrs)
    |> Repo.insert()
  end

  @doc "Updates an existing book."
  def update_book(%Book{} = book, attrs) do
    book
    |> Book.changeset(attrs)
    |> Repo.update()
  end

  @doc "Deletes a book."
  def delete_book(%Book{} = book), do: Repo.delete(book)
end
