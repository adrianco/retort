defmodule BooksApi.Router do
  @moduledoc "HTTP routes for the books API. All bodies are JSON."
  use Plug.Router

  alias BooksApi.Book

  plug(:match)

  plug(Plug.Parsers,
    parsers: [:json],
    pass: ["application/json"],
    json_decoder: Jason
  )

  plug(:dispatch)

  get "/health" do
    json(conn, 200, %{status: "ok"})
  end

  post "/books" do
    case Book.create(conn.body_params) do
      {:ok, book} -> json(conn, 201, book)
      {:error, errors} -> validation_error(conn, errors)
    end
  end

  get "/books" do
    case Book.list(conn.params["author"]) do
      {:ok, books} -> json(conn, 200, books)
      {:error, _} -> json(conn, 500, %{error: "internal error"})
    end
  end

  get "/books/:id" do
    with {:ok, id} <- parse_id(id),
         {:ok, book} <- Book.get(id) do
      json(conn, 200, book)
    else
      _ -> not_found(conn)
    end
  end

  put "/books/:id" do
    with {:ok, id} <- parse_id(id),
         {:ok, book} <- Book.update(id, conn.body_params) do
      json(conn, 200, book)
    else
      {:error, :not_found} -> not_found(conn)
      {:error, errors} when is_map(errors) -> validation_error(conn, errors)
      _ -> not_found(conn)
    end
  end

  delete "/books/:id" do
    with {:ok, id} <- parse_id(id),
         :ok <- Book.delete(id) do
      send_resp(conn, 204, "")
    else
      _ -> not_found(conn)
    end
  end

  match _ do
    json(conn, 404, %{error: "not found"})
  end

  defp parse_id(raw) do
    case Integer.parse(raw) do
      {id, ""} -> {:ok, id}
      _ -> :error
    end
  end

  defp not_found(conn), do: json(conn, 404, %{error: "book not found"})

  defp validation_error(conn, errors),
    do: json(conn, 422, %{error: "validation failed", details: errors})

  defp json(conn, status, body) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(body))
  end
end
