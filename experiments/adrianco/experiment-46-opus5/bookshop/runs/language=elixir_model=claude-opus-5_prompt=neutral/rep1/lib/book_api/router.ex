defmodule BookApi.Router do
  @moduledoc """
  HTTP routing for the book collection API.

  All responses are JSON. Errors use the shape
  `{"error": "...", "details": {...}}`.
  """

  use Plug.Router
  use Plug.ErrorHandler

  alias BookApi.Books

  plug(:match)
  plug(:fetch_query_params)

  plug(BookApi.Plugs.JsonBody,
    parsers: [:json],
    pass: ["application/json"],
    json_decoder: Jason
  )

  plug(:dispatch)

  get "/health" do
    status = if repo_alive?(), do: "ok", else: "degraded"
    code = if status == "ok", do: 200, else: 503

    send_json(conn, code, %{status: status, service: "book_api"})
  end

  post "/books" do
    case Books.create_book(book_params(conn)) do
      {:ok, book} ->
        conn
        |> put_resp_header("location", "/books/#{book.id}")
        |> send_json(201, book)

      {:error, changeset} ->
        send_validation_error(conn, changeset)
    end
  end

  get "/books" do
    books = Books.list_books(author: conn.params["author"])
    send_json(conn, 200, books)
  end

  get "/books/:id" do
    with_book(conn, id, fn book -> send_json(conn, 200, book) end)
  end

  put "/books/:id" do
    with_book(conn, id, fn book ->
      case Books.update_book(book, book_params(conn)) do
        {:ok, updated} -> send_json(conn, 200, updated)
        {:error, changeset} -> send_validation_error(conn, changeset)
      end
    end)
  end

  delete "/books/:id" do
    with_book(conn, id, fn book ->
      {:ok, _} = Books.delete_book(book)
      send_resp(conn, 204, "")
    end)
  end

  match _ do
    send_json(conn, 404, %{error: "Not found"})
  end

  ## Helpers

  defp with_book(conn, id, fun) do
    case Books.get_book(id) do
      nil -> send_json(conn, 404, %{error: "Book not found"})
      book -> fun.(book)
    end
  end

  # Only the writable book attributes are taken from the request, so that
  # clients cannot set `id` or the timestamps.
  defp book_params(conn) do
    conn.body_params
    |> case do
      params when is_map(params) -> params
      _ -> %{}
    end
    |> Map.take(["title", "author", "year", "isbn"])
  end

  defp send_json(conn, status, body) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(body))
  end

  defp send_validation_error(conn, changeset) do
    send_json(conn, 422, %{error: "Validation failed", details: translate_errors(changeset)})
  end

  defp translate_errors(changeset) do
    Ecto.Changeset.traverse_errors(changeset, fn {msg, opts} ->
      Regex.replace(~r"%{(\w+)}", msg, fn _, key ->
        opts |> Keyword.get(String.to_existing_atom(key), key) |> to_string()
      end)
    end)
  end

  defp repo_alive? do
    match?({:ok, _}, Ecto.Adapters.SQL.query(BookApi.Repo, "SELECT 1", []))
  rescue
    _ -> false
  end

  @impl Plug.ErrorHandler
  def handle_errors(conn, %{status: status}) do
    send_json(conn, status, %{error: "Internal server error"})
  end
end
