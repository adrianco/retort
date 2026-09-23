defmodule Books.Router do
  use Plug.Router
  use Plug.ErrorHandler
  alias Books.{Repo, Validator}

  plug Plug.Parsers, parsers: [:json], json_decoder: Jason, pass: ["*/*"]
  plug :match
  plug :dispatch

  get "/health", do: json(conn, 200, %{status: "ok"})

  get "/books" do
    conn = fetch_query_params(conn)
    json(conn, 200, Repo.list(conn.query_params["author"]))
  end

  post "/books" do
    with {:ok, attrs} <- Validator.validate(body(conn)), {:ok, book} <- Repo.create(attrs) do
      json(conn, 201, book)
    else
      err -> error(conn, err)
    end
  end

  get "/books/:id" do
    with {:ok, id} <- parse_id(id), {:ok, book} <- Repo.get(id), do: json(conn, 200, book), else: (err -> error(conn, err))
  end

  put "/books/:id" do
    with {:ok, id} <- parse_id(id),
         {:ok, attrs} <- Validator.validate(body(conn)),
         {:ok, book} <- Repo.update(id, attrs) do
      json(conn, 200, book)
    else
      err -> error(conn, err)
    end
  end

  delete "/books/:id" do
    with {:ok, id} <- parse_id(id), :ok <- Repo.delete(id), do: send_resp(conn, 204, ""), else: (err -> error(conn, err))
  end

  match _, do: json(conn, 404, %{error: "not found"})

  # Plug.Parsers puts non-object JSON bodies under "_json"
  defp body(%{body_params: %{"_json" => v}}), do: v
  defp body(conn), do: conn.body_params

  defp parse_id(id) do
    case Integer.parse(id) do
      {n, ""} -> {:ok, n}
      _ -> {:error, :not_found}
    end
  end

  defp error(conn, {:error, :not_found}), do: json(conn, 404, %{error: "book not found"})
  defp error(conn, {:error, errors}), do: json(conn, 422, %{errors: errors})

  defp json(conn, status, data) do
    conn |> put_resp_content_type("application/json") |> send_resp(status, Jason.encode!(data))
  end

  @impl Plug.ErrorHandler
  def handle_errors(conn, %{reason: %Plug.Parsers.ParseError{}}), do: json(conn, 400, %{error: "invalid JSON"})
  def handle_errors(conn, _), do: json(conn, conn.status, %{error: "internal error"})
end
