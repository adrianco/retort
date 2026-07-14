defmodule BookApi.Router do
  @moduledoc """
  HTTP router exposing the book collection REST API.
  """
  use Plug.Router

  alias BookApi.Books

  plug :match
  plug Plug.Parsers, parsers: [:json], pass: ["application/json"], json_decoder: Jason
  plug :dispatch

  get "/health" do
    send_json(conn, 200, %{status: "ok"})
  end

  post "/books" do
    case Books.create_book(conn.body_params) do
      {:ok, book} ->
        send_json(conn, 201, book)

      {:error, changeset} ->
        send_json(conn, 422, %{errors: format_errors(changeset)})
    end
  end

  get "/books" do
    books = Books.list_books(author: conn.query_params["author"])
    send_json(conn, 200, books)
  end

  get "/books/:id" do
    case Books.get_book(id) do
      nil -> send_json(conn, 404, %{error: "book not found"})
      book -> send_json(conn, 200, book)
    end
  end

  put "/books/:id" do
    case Books.get_book(id) do
      nil ->
        send_json(conn, 404, %{error: "book not found"})

      book ->
        case Books.update_book(book, conn.body_params) do
          {:ok, updated} -> send_json(conn, 200, updated)
          {:error, changeset} -> send_json(conn, 422, %{errors: format_errors(changeset)})
        end
    end
  end

  delete "/books/:id" do
    case Books.get_book(id) do
      nil -> send_json(conn, 404, %{error: "book not found"})
      book ->
        {:ok, _} = Books.delete_book(book)
        send_resp(conn, 204, "")
    end
  end

  match _ do
    send_json(conn, 404, %{error: "not found"})
  end

  defp send_json(conn, status, body) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(body))
  end

  defp format_errors(changeset) do
    Ecto.Changeset.traverse_errors(changeset, fn {msg, opts} ->
      Enum.reduce(opts, msg, fn {key, value}, acc ->
        String.replace(acc, "%{#{key}}", to_string(value))
      end)
    end)
  end
end
