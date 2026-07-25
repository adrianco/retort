defmodule BooksApi.Books do
  @moduledoc "CRUD operations for books."

  import Ecto.Query

  alias BooksApi.{Book, Repo}

  def list_books(filters \\ %{}) do
    Book
    |> filter_by_author(filters[:author])
    |> order_by(asc: :id)
    |> Repo.all()
  end

  defp filter_by_author(query, nil), do: query
  defp filter_by_author(query, author), do: where(query, [b], b.author == ^author)

  def get_book(id), do: Repo.get(Book, id)

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
