defmodule BookApiWeb.BookController do
  use BookApiWeb, :controller

  alias BookApi.Books
  alias BookApi.Books.Book

  # List all books (supports ?author= filter via conn.query_params)
  def index(conn, %{"author" => author}) do
    books = Books.list_books(author)
    json(conn, %{data: books})
  end

  def index(conn, _params) do
    books = Books.list_books()
    json(conn, %{data: books})
  end

  # Create a new book
  def create(conn, params) do
    case Books.create_book(params) do
      {:ok, book} ->
        conn
        |> put_status(:created)
        |> json(%{data: book})

      {:error, %Ecto.Changeset{} = changeset} ->
        conn
        |> put_status(:unprocessable_entity)
        |> json(%{
          error: "Validation failed",
          details: changeset_errors(changeset)
        })
    end
  end

  # Get a single book by ID
  def show(conn, %{"id" => id}) do
    case Books.get_book(id) do
      {:ok, book} ->
        json(conn, %{data: book})

      {:error, :not_found} ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "Book not found"})
    end
  end

  # Update a book
  def update(conn, %{"id" => id} = params) do
    case Books.get_book(id) do
      {:ok, book} ->
        case Books.update_book(book, params) do
          {:ok, book} ->
            json(conn, %{data: book})

          {:error, %Ecto.Changeset{} = changeset} ->
            conn
            |> put_status(:unprocessable_entity)
            |> json(%{
              error: "Validation failed",
              details: changeset_errors(changeset)
            })
        end

      {:error, :not_found} ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "Book not found"})
    end
  end

  # Delete a book
  def delete(conn, %{"id" => id}) do
    case Books.get_book(id) do
      {:ok, book} ->
        case Books.delete_book(book) do
          {:ok, deleted_book} ->
            json(conn, %{data: deleted_book})

          {:error, changeset} ->
            conn
            |> put_status(:unprocessable_entity)
            |> json(%{error: "Could not delete book", details: changeset_errors(changeset)})
        end

      {:error, :not_found} ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "Book not found"})
    end
  end

  # Convert Ecto changeset errors to a serializable map
  defp changeset_errors(changeset) do
    Ecto.Changeset.traverse_errors(changeset, fn {msg, opts} ->
      Enum.reduce(opts, msg, fn {key, value}, acc ->
        String.replace(acc, "{#{key}}", to_string(value))
      end)
    end)
  end
end
