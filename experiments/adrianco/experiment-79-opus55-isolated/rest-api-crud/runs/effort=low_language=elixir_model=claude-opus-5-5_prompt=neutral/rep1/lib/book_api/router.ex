defmodule BookApi.Router do
  @moduledoc """
  HTTP routes for the book collection API.
  """
  use Plug.Router
  use Plug.ErrorHandler

  alias BookApi.{Book, Store}

  plug(Plug.Logger)
  plug(:match)
  plug(Plug.Parsers, parsers: [:json], pass: ["*/*"], json_decoder: Jason)
  plug(:dispatch)

  get "/health" do
    json(conn, 200, %{status: "ok"})
  end

  post "/books" do
    with {:ok, attrs} <- validate(conn) do
      json(conn, 201, Store.create(attrs))
    else
      {:error, errors} -> validation_failed(conn, errors)
    end
  end

  get "/books" do
    conn = fetch_query_params(conn)

    case conn.query_params["author"] do
      author when is_binary(author) and author != "" -> json(conn, 200, Store.list(author))
      _ -> json(conn, 200, Store.list())
    end
  end

  get "/books/:id" do
    with {:ok, id} <- parse_id(id),
         {:ok, book} <- Store.get(id) do
      json(conn, 200, book)
    else
      _ -> not_found(conn)
    end
  end

  put "/books/:id" do
    with {:id, {:ok, id}} <- {:id, parse_id(id)},
         {:ok, attrs} <- validate(conn),
         {:id, {:ok, book}} <- {:id, Store.update(id, attrs)} do
      json(conn, 200, book)
    else
      {:id, _} -> not_found(conn)
      {:error, errors} -> validation_failed(conn, errors)
    end
  end

  delete "/books/:id" do
    with {:ok, id} <- parse_id(id),
         :ok <- Store.delete(id) do
      send_resp(conn, 204, "")
    else
      _ -> not_found(conn)
    end
  end

  match _ do
    json(conn, 404, %{error: "Not found"})
  end

  @impl Plug.ErrorHandler
  def handle_errors(conn, %{reason: %Plug.Parsers.ParseError{}}) do
    json(conn, 400, %{error: "Malformed JSON body"})
  end

  def handle_errors(conn, %{reason: %Plug.Parsers.UnsupportedMediaTypeError{}}) do
    json(conn, 415, %{error: "Unsupported media type"})
  end

  def handle_errors(conn, _) do
    json(conn, conn.status || 500, %{error: "Internal server error"})
  end

  # A non-object JSON body (e.g. an array) is wrapped by Plug under "_json".
  defp validate(%{body_params: %{"_json" => _}}), do: Book.validate(nil)
  defp validate(%{body_params: %Plug.Conn.Unfetched{}}), do: Book.validate(%{})
  defp validate(conn), do: Book.validate(conn.body_params)

  defp parse_id(raw) do
    case Integer.parse(raw) do
      {id, ""} when id > 0 -> {:ok, id}
      _ -> :error
    end
  end

  defp not_found(conn), do: json(conn, 404, %{error: "Book not found"})

  defp validation_failed(conn, errors) do
    json(conn, 422, %{error: "Validation failed", details: errors})
  end

  defp json(conn, status, body) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(body))
  end
end
