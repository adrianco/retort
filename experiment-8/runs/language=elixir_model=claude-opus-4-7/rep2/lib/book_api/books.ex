defmodule BookApi.Books do
  @moduledoc "Context for managing books."

  import Ecto.Query, warn: false

  alias BookApi.Repo
  alias BookApi.Book

  def list_books(filters \\ %{}) do
    Book
    |> filter_by_author(filters[:author] || filters["author"])
    |> order_by([b], asc: b.id)
    |> Repo.all()
  end

  defp filter_by_author(query, nil), do: query
  defp filter_by_author(query, ""), do: query
  defp filter_by_author(query, author), do: where(query, [b], b.author == ^author)

  def get_book(id) when is_integer(id), do: Repo.get(Book, id)

  def get_book(id) when is_binary(id) do
    case Integer.parse(id) do
      {int_id, ""} -> Repo.get(Book, int_id)
      _ -> nil
    end
  end

  def create_book(attrs) do
    %Book{}
    |> Book.changeset(attrs)
    |> Repo.insert()
  end

  def update_book(%Book{} = book, attrs) do
    book
    |> Book.changeset(attrs)
    |> Repo.update()
  end

  def delete_book(%Book{} = book), do: Repo.delete(book)
end
