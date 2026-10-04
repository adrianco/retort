defmodule BookApi.Router do
  @moduledoc "HTTP routes for the book collection API."
  use Plug.Router
  use Plug.ErrorHandler

  alias BookApi.{Book, Store}

  plug(:match)
  plug(Plug.Parsers, parsers: [:json], pass: ["*/*"], json_decoder: Jason)
  plug(:dispatch)

  get "/health" do
    json(conn, 200, %{status: "ok"})
  end

  post "/books" do
    with {:ok, attrs} <- validate(conn),
         {:ok, book} <- Store.create(attrs) do
      json(conn, 201, book)
    else
      error -> error(conn, error)
    end
  end

  get "/books" do
    conn = fetch_query_params(conn)

    author =
      case conn.query_params["author"] do
        value when is_binary(value) and value != "" -> value
        _ -> nil
      end

    json(conn, 200, Store.list(author))
  end

  get "/books/:id" do
    with {:ok, id} <- parse_id(id),
         {:ok, book} <- Store.get(id) do
      json(conn, 200, book)
    else
      error -> error(conn, error)
    end
  end

  put "/books/:id" do
    with {:ok, id} <- parse_id(id),
         {:ok, attrs} <- validate(conn),
         {:ok, book} <- Store.update(id, attrs) do
      json(conn, 200, book)
    else
      error -> error(conn, error)
    end
  end

  delete "/books/:id" do
    with {:ok, id} <- parse_id(id),
         :ok <- Store.delete(id) do
      send_resp(conn, 204, "")
    else
      error -> error(conn, error)
    end
  end

  match _ do
    json(conn, 404, %{error: "not found"})
  end

  @impl Plug.ErrorHandler
  def handle_errors(conn, %{reason: %Plug.Parsers.ParseError{}}) do
    json(conn, 400, %{error: "invalid JSON"})
  end

  def handle_errors(conn, %{reason: %Plug.Parsers.UnsupportedMediaTypeError{}}) do
    json(conn, 415, %{error: "unsupported media type"})
  end

  def handle_errors(conn, _) do
    json(conn, conn.status || 500, %{error: "internal server error"})
  end

  # A non-object JSON body is parsed into %{"_json" => value}.
  defp validate(%{body_params: %{"_json" => _}}), do: {:error, :not_an_object}
  defp validate(%{body_params: %Plug.Conn.Unfetched{}}), do: Book.validate(%{})
  defp validate(%{body_params: params}), do: Book.validate(params)

  # SQLite ids are positive 64-bit integers; anything else cannot exist.
  defp parse_id(raw) do
    case Integer.parse(raw) do
      {id, ""} when id > 0 and id < 0x8000000000000000 -> {:ok, id}
      _ -> {:error, :not_found}
    end
  end

  defp error(conn, {:error, :not_found}), do: json(conn, 404, %{error: "book not found"})

  defp error(conn, {:error, :not_an_object}),
    do: json(conn, 400, %{error: "request body must be a JSON object"})

  defp error(conn, {:error, errors}) when is_map(errors),
    do: json(conn, 422, %{error: "validation failed", details: errors})

  defp json(conn, status, body) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(body))
  end
end
