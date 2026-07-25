defmodule BookAPIWeb.Router do
  use Plug.Router

  plug :match
  plug :dispatch

  get "/health" do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(200, ~s({"status":"ok"}))
  end

  get "/books" do
    books = BookAPI.Books.list_books(conn.query_params)
    json(conn, %{data: books})
  end

  get "/books/:id" do
    try do
      book = BookAPI.Books.get_book!(id)
      json(conn, %{data: book})
    rescue
      Ecto.NoResultsError -> json(conn, %{errors: %{detail: "Not Found"}})
    end
  end

  post "/books" do
    case BookAPI.Books.create_book(conn.body_params) do
      {:ok, book} ->
        conn
        |> put_resp_header("location", "/api/books/#{book.id}")
        |> put_resp_content_type("application/json")
        |> send_resp(201, Jason.encode!(%{data: book}))
      {:error, changeset} ->
        json(conn, %{errors: changeset.errors})
    end
  end

  put "/books/:id" do
    try do
      book = BookAPI.Books.get_book!(id)
      case BookAPI.Books.update_book(book, conn.body_params) do
        {:ok, book} -> json(conn, %{data: book})
        {:error, changeset} -> json(conn, %{errors: changeset.errors})
      end
    rescue
      Ecto.NoResultsError -> json(conn, %{errors: %{detail: "Not Found"}})
    end
  end

  delete "/books/:id" do
    try do
      book = BookAPI.Books.get_book!(id)
      case BookAPI.Books.delete_book(book) do
        {:ok, _} -> send_resp(conn, 204, "")
        {:error, _changeset} -> json(conn, %{errors: %{detail: "Not Found"}})
      end
    rescue
      Ecto.NoResultsError -> json(conn, %{errors: %{detail: "Not Found"}})
    end
  end

  match _ do
    json(conn, %{errors: %{detail: "Not Found"}})
  end
end
