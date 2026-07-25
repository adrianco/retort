defmodule BookApi.Web.BookController do
  use BookApi.Web, :controller

  alias BookApi.Book
  alias BookApi.Repo
  import Ecto.Query

  def index(conn, params) do
    books = case params["author"] do
      nil -> Repo.all(Book)
      author -> Repo.all(from b in Book, where: b.author == ^author)
    end

    conn
    |> put_status(:ok)
    |> json(%{data: books})
  end

  def show(conn, %{"id" => id}) do
    case Repo.get(Book, id) do
      nil ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "Book not found"})

      book ->
        conn
        |> put_status(:ok)
        |> json(%{data: book})
    end
  end

  def create(conn, params) do
    case Book.changeset(%Book{}, params) do
      %{valid?: true} = changeset ->
        case Repo.insert(changeset) do
          {:ok, book} ->
            conn
            |> put_status(:created)
            |> json(%{data: book})

          {:error, %Ecto.Changeset{} = changeset} ->
            conn
            |> put_status(:unprocessable_entity)
            |> json(%{errors: changeset.errors})
        end

      %{valid?: false} = changeset ->
        conn
        |> put_status(:unprocessable_entity)
        |> json(%{errors: changeset.errors})
    end
  end

  def update(conn, %{"id" => id} = params) do
    case Repo.get(Book, id) do
      nil ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "Book not found"})

      book ->
        case Book.changeset(book, params) do
          %{valid?: true} = changeset ->
            case Repo.update(changeset) do
              {:ok, book} ->
                conn
                |> put_status(:ok)
                |> json(%{data: book})

              {:error, %Ecto.Changeset{} = changeset} ->
                conn
                |> put_status(:unprocessable_entity)
                |> json(%{errors: changeset.errors})
            end

          %{valid?: false} = changeset ->
            conn
            |> put_status(:unprocessable_entity)
            |> json(%{errors: changeset.errors})
        end
    end
  end

  def delete(conn, %{"id" => id}) do
    case Repo.get(Book, id) do
      nil ->
        conn
        |> put_status(:not_found)
        |> json(%{error: "Book not found"})

      book ->
        case Repo.delete(book) do
          {:ok, _book} ->
            conn
            |> put_status(:no_content)
            |> json(%{})

          {:error, %Ecto.Changeset{} = changeset} ->
            conn
            |> put_status(:unprocessable_entity)
            |> json(%{errors: changeset.errors})
        end
    end
  end
end
