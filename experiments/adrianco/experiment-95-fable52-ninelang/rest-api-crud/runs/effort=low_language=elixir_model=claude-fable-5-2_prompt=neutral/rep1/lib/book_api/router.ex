defmodule BookApi.Router do
  @moduledoc "HTTP routes for the book collection API."
  use Plug.Router

  alias BookApi.{Book, Store}

  plug(:match)
  plug(:dispatch)

  get "/health" do
    json(conn, 200, %{status: "ok"})
  end

  get "/books" do
    conn = fetch_query_params(conn)

    filters =
      case conn.query_params do
        %{"author" => author} when is_binary(author) -> %{author: author}
        _ -> %{}
      end

    json(conn, 200, Store.list(filters))
  end

  post "/books" do
    with {:ok, params, conn} <- read_json(conn),
         {:ok, attrs} <- Book.validate(params),
         {:ok, book} <- Store.create(attrs) do
      conn
      |> put_resp_header("location", "/books/#{book.id}")
      |> json(201, book)
    else
      error -> handle_error(conn, error)
    end
  end

  get "/books/:id" do
    with {:ok, id} <- parse_id(id),
         {:ok, book} <- Store.get(id) do
      json(conn, 200, book)
    else
      error -> handle_error(conn, error)
    end
  end

  put "/books/:id" do
    with {:ok, id} <- parse_id(id),
         {:ok, _existing} <- Store.get(id),
         {:ok, params, conn} <- read_json(conn),
         {:ok, attrs} <- Book.validate(params),
         {:ok, book} <- Store.update(id, attrs) do
      json(conn, 200, book)
    else
      error -> handle_error(conn, error)
    end
  end

  delete "/books/:id" do
    with {:ok, id} <- parse_id(id),
         :ok <- Store.delete(id) do
      send_resp(conn, 204, "")
    else
      error -> handle_error(conn, error)
    end
  end

  match _ do
    json(conn, 404, %{error: "not found"})
  end

  defp handle_error(conn, {:error, :not_found}), do: json(conn, 404, %{error: "book not found"})

  defp handle_error(conn, {:error, :invalid_json}),
    do: json(conn, 400, %{error: "invalid JSON body"})

  defp handle_error(conn, {:error, :too_large}),
    do: json(conn, 413, %{error: "request body too large"})

  defp handle_error(conn, {:error, errors}) when is_map(errors),
    do: json(conn, 422, %{error: "validation failed", details: errors})

  # Non-numeric ids can never match a book.
  defp parse_id(raw) do
    case Integer.parse(raw) do
      {id, ""} when id > 0 -> {:ok, id}
      _ -> {:error, :not_found}
    end
  end

  defp read_json(conn) do
    case read_body(conn, length: 1_000_000) do
      {:ok, body, conn} ->
        case JSON.decode(body) do
          {:ok, params} -> {:ok, params, conn}
          {:error, _} -> {:error, :invalid_json}
        end

      {:more, _, _} ->
        {:error, :too_large}

      {:error, _} ->
        {:error, :invalid_json}
    end
  end

  defp json(conn, status, data) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, JSON.encode!(data))
  end
end
