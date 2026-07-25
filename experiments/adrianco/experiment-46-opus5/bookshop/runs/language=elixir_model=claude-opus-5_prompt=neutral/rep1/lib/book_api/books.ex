defmodule BookApi.Books do
  @moduledoc """
  The Books context: all persistence operations for the book collection.
  """

  import Ecto.Query, warn: false

  alias BookApi.Books.Book
  alias BookApi.Repo

  @doc """
  Lists books, newest first.

  Supported options:

    * `:author` — case-insensitive substring match on the author name.
  """
  def list_books(opts \\ []) do
    Book
    |> filter_by_author(opts[:author])
    |> order_by([b], desc: b.id)
    |> Repo.all()
  end

  defp filter_by_author(query, author) when is_binary(author) do
    case String.trim(author) do
      "" ->
        query

      term ->
        where(
          query,
          [b],
          like(fragment("lower(?)", b.author), ^"%#{escape_like(String.downcase(term))}%")
        )
    end
  end

  defp filter_by_author(query, _), do: query

  # `%`, `_` and `\` are LIKE wildcards/escapes and must not leak in from user input.
  defp escape_like(term) do
    String.replace(term, ~r/[\\%_]/, "\\\\\\0")
  end

  @doc "Fetches a book by id. Returns `nil` when it does not exist."
  def get_book(id) when is_integer(id), do: Repo.get(Book, id)

  def get_book(id) when is_binary(id) do
    case Integer.parse(id) do
      {int_id, ""} -> get_book(int_id)
      _ -> nil
    end
  end

  def get_book(_), do: nil

  @doc "Creates a book. Returns `{:ok, book}` or `{:error, changeset}`."
  def create_book(attrs) do
    %Book{}
    |> Book.changeset(attrs)
    |> Repo.insert()
  end

  @doc "Updates a book. Returns `{:ok, book}` or `{:error, changeset}`."
  def update_book(%Book{} = book, attrs) do
    book
    |> Book.changeset(attrs)
    |> Repo.update()
  end

  @doc "Deletes a book."
  def delete_book(%Book{} = book), do: Repo.delete(book)
end
