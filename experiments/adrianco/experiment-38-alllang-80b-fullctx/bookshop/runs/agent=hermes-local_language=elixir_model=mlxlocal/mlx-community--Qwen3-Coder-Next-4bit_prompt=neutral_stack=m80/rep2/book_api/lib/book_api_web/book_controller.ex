defmodule BookApiWeb.BookController do
  use BookApiWeb, :controller

  alias BookApi.Book
  alias BookApi.Repo

  action_fallback BookApiWeb.FallbackController

  def index(conn, params) do
    books = case params["author"] do
      nil -> Repo.all(Book)
      author -> Repo.all(from b in Book, where: ilike(b.author, ^"%#{author}%"))
    end
    render(conn, :index, books: books)
  end

  def show(conn, %{"id" => id}) do
    book = Repo.get!(Book, id)
    render(conn, :show, book: book)
  end

  def create(conn, %{"book" => book_params}) do
    with {:ok, %Book{} = book} <- Repo.insert(Book.changeset(%Book{}, book_params)) do
      conn
      |> put_status(:created)
      |> render(:show, book: book)
    end
  end

  def update(conn, %{"id" => id, "book" => book_params}) do
    book = Repo.get!(Book, id)
    
    with {:ok, %Book{} = book} <- Repo.update(Book.changeset(book, book_params)) do
      render(conn, :show, book: book)
    end
  end

  def delete(conn, %{"id" => id}) do
    book = Repo.get!(Book, id)
    
    with {:ok, %Book{}} <- Repo.delete(book) do
      send_resp(conn, :no_content, "")
    end
  end
end
