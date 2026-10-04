defmodule BookApi.Router do
  @moduledoc "HTTP routes for the book collection API."
  use Plug.Router

  alias BookApi.{Book, Store}

  # Largest rowid SQLite can hold; anything beyond cannot exist.
  @max_id 9_223_372_036_854_775_807

  plug(:match)
  plug(:dispatch)

  get "/health" do
    json(conn, 200, %{status: "ok"})
  end

  post "/books" do
    with {:ok, params} <- read_json(conn),
         {:ok, attrs} <- Book.validate(params),
         {:ok, book} <- Store.create(attrs) do
      json(conn, 201, book)
    else
      error -> error_response(conn, error)
    end
  end

  get "/books" do
    conn = fetch_query_params(conn)

    author =
      case conn.query_params["author"] do
        author when is_binary(author) and author != "" -> author
        _ -> nil
      end

    json(conn, 200, Store.list(author))
  end

  get "/books/:id" do
    with {:ok, id} <- parse_id(id),
         {:ok, book} <- Store.get(id) do
      json(conn, 200, book)
    else
      error -> error_response(conn, error)
    end
  end

  put "/books/:id" do
    with {:ok, id} <- parse_id(id),
         {:ok, params} <- read_json(conn),
         {:ok, attrs} <- Book.validate(params),
         {:ok, book} <- Store.update(id, attrs) do
      json(conn, 200, book)
    else
      error -> error_response(conn, error)
    end
  end

  delete "/books/:id" do
    with {:ok, id} <- parse_id(id),
         :ok <- Store.delete(id) do
      send_resp(conn, 204, "")
    else
      error -> error_response(conn, error)
    end
  end

  match _ do
    json(conn, 404, %{error: "not found"})
  end

  defp parse_id(raw) do
    case Integer.parse(raw) do
      {id, ""} when id > 0 and id <= @max_id -> {:ok, id}
      _ -> {:error, :not_found}
    end
  end

  defp read_json(conn) do
    with {:ok, body, _conn} <- read_body(conn, length: 1_000_000),
         {:ok, decoded} <- Jason.decode(body) do
      {:ok, decoded}
    else
      {:more, _, _} -> {:error, :too_large}
      _ -> {:error, :bad_json}
    end
  end

  defp error_response(conn, {:error, :not_found}), do: json(conn, 404, %{error: "book not found"})

  defp error_response(conn, {:error, :bad_json}),
    do: json(conn, 400, %{error: "invalid JSON body"})

  defp error_response(conn, {:error, :too_large}),
    do: json(conn, 413, %{error: "request body too large"})

  defp error_response(conn, {:error, errors}) when is_map(errors),
    do: json(conn, 422, %{error: "validation failed", details: errors})

  defp json(conn, status, body) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(body))
  end
end
