defmodule BookApi.Books do
  @moduledoc """
  The Books context. Provides CRUD operations for books
  and a list-all endpoint with author filtering.
  """

  import Ecto.Query, warn: false
  alias BookApi.Repo
  alias BookApi.Books.Book

  @doc """
  List all books, optionally filtered by author (case-insensitive partial match).
  """
  def list_books(author \\ nil) do
    query = from b in Book, order_by: [asc: b.inserted_at]

    if author do
      from b in query, where: ilike(b.author, ^("%" <> author <> "%"))
    else
      query
    end
    |> Repo.all()
  end

  @doc """
  Get a single book by ID. Raises if not found.
  """
  def get_book!(id) do
    Repo.get!(Book, id)
  end

  @doc """
  Get a single book by ID, returns {:ok, book} or {:error, :not_found}.
  """
  def get_book(id) do
    case Repo.get(Book, id) do
      nil -> {:error, :not_found}
      book -> {:ok, book}
    end
  end

  @doc """
  Create a new book from attrs.
  """
  def create_book(attrs \\ %{}) do
    %Book{}
    |> Book.changeset(attrs)
    |> Repo.insert()
  end

  @doc """
  Update an existing book.
  """
  def update_book(%Book{} = book, attrs) do
    book
    |> Book.changeset(attrs)
    |> Repo.update()
  end

  @doc """
  Delete a book.
  """
  def delete_book(%Book{} = book) do
    Repo.delete(book)
  end
end
