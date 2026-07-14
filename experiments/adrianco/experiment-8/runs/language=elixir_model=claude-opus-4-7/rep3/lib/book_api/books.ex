defmodule BookApi.Books do
  @moduledoc false

  import Ecto.Query
  alias BookApi.{Book, Repo}

  def list_books(opts \\ []) do
    query = from b in Book, order_by: [asc: b.id]

    query =
      case Keyword.get(opts, :author) do
        nil -> query
        "" -> query
        author -> from b in query, where: b.author == ^author
      end

    Repo.all(query)
  end

  def get_book(id) when is_integer(id) or is_binary(id) do
    case parse_id(id) do
      {:ok, int_id} -> Repo.get(Book, int_id)
      :error -> nil
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

  defp parse_id(id) when is_integer(id), do: {:ok, id}
  defp parse_id(id) when is_binary(id) do
    case Integer.parse(id) do
      {n, ""} -> {:ok, n}
      _ -> :error
    end
  end
end
