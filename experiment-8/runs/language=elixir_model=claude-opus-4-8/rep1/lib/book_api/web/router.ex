defmodule BookApi.Web.Router do
  @moduledoc """
  HTTP router for the book collection API.

  All responses are JSON. Validation errors return 422 with a map of
  field => messages; missing resources return 404.
  """
  use Plug.Router

  alias BookApi.Books
  alias BookApi.Book

  plug :match

  plug Plug.Parsers,
    parsers: [:json],
    pass: ["application/json"],
    json_decoder: Jason

  plug :dispatch

  # Health check
  get "/health" do
    send_json(conn, 200, %{status: "ok"})
  end

  # List books, optional ?author= filter
  get "/books" do
    conn = fetch_query_params(conn)
    books = Books.list_books(author: conn.query_params["author"])
    send_json(conn, 200, books)
  end

  # Get a single book
  get "/books/:id" do
    case Books.get_book(id) do
      %Book{} = book -> send_json(conn, 200, book)
      nil -> send_json(conn, 404, %{error: "book not found"})
    end
  end

  # Create a book
  post "/books" do
    case Books.create_book(conn.body_params) do
      {:ok, book} ->
        send_json(conn, 201, book)

      {:error, changeset} ->
        send_json(conn, 422, %{errors: translate_errors(changeset)})
    end
  end

  # Update a book
  put "/books/:id" do
    case Books.get_book(id) do
      nil ->
        send_json(conn, 404, %{error: "book not found"})

      %Book{} = book ->
        case Books.update_book(book, conn.body_params) do
          {:ok, updated} -> send_json(conn, 200, updated)
          {:error, changeset} -> send_json(conn, 422, %{errors: translate_errors(changeset)})
        end
    end
  end

  # Delete a book
  delete "/books/:id" do
    case Books.get_book(id) do
      nil ->
        send_json(conn, 404, %{error: "book not found"})

      %Book{} = book ->
        {:ok, _} = Books.delete_book(book)
        send_resp(conn, 204, "")
    end
  end

  match _ do
    send_json(conn, 404, %{error: "not found"})
  end

  # --- helpers ---

  defp send_json(conn, status, body) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(body))
  end

  defp translate_errors(changeset) do
    Ecto.Changeset.traverse_errors(changeset, fn {msg, opts} ->
      Enum.reduce(opts, msg, fn {key, value}, acc ->
        String.replace(acc, "%{#{key}}", to_string(value))
      end)
    end)
  end
end
