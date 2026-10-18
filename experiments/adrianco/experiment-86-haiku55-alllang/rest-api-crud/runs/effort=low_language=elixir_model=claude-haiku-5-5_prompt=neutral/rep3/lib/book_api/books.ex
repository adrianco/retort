defmodule BookApi.Books do
  @moduledoc "Context module for book persistence."
  import Ecto.Query

  alias BookApi.{Book, Repo}

  def list_books(filters \\ %{}) do
    Book
    |> maybe_filter_author(filters["author"])
    |> order_by(asc: :id)
    |> Repo.all()
  end

  def get_book(id), do: Repo.get(Book, id)

  def create_book(attrs) do
    %Book{} |> Book.changeset(attrs) |> Repo.insert()
  end

  def update_book(%Book{} = book, attrs) do
    book |> Book.changeset(attrs) |> Repo.update()
  end

  def delete_book(%Book{} = book), do: Repo.delete(book)

  defp maybe_filter_author(query, author) when is_binary(author) and author != "" do
    where(query, [b], b.author == ^author)
  end

  defp maybe_filter_author(query, _), do: query
end
