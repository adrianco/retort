defmodule Books.Router do
  use Plug.Router
  alias Books.Repo

  plug Plug.Parsers, parsers: [:json], json_decoder: Jason
  plug :match
  plug :dispatch

  get "/health", do: json(conn, 200, %{status: "ok"})

  get "/books" do
    conn = Plug.Conn.fetch_query_params(conn)
    json(conn, 200, Repo.list(blank_to_nil(conn.query_params["author"])))
  end

  post "/books" do
    with {:ok, attrs} <- validate(conn.body_params) do
      {:ok, book} = Repo.create(attrs)
      json(conn, 201, book)
    else
      {:error, errors} -> json(conn, 422, %{errors: errors})
    end
  end

  get "/books/:id" do
    with {:ok, id} <- parse_id(id), {:ok, book} <- Repo.get(id) do
      json(conn, 200, book)
    else
      _ -> not_found(conn)
    end
  end

  put "/books/:id" do
    with {:ok, id} <- parse_id(id),
         {:ok, _} <- Repo.get(id),
         {:ok, attrs} <- validate(conn.body_params),
         {:ok, book} <- Repo.update(id, attrs) do
      json(conn, 200, book)
    else
      {:error, errors} when is_map(errors) -> json(conn, 422, %{errors: errors})
      _ -> not_found(conn)
    end
  end

  delete "/books/:id" do
    with {:ok, id} <- parse_id(id), :ok <- Repo.delete(id) do
      Plug.Conn.send_resp(conn, 204, "")
    else
      _ -> not_found(conn)
    end
  end

  match _, do: json(conn, 404, %{error: "not found"})

  @doc false
  def validate(params) when is_map(params) do
    errors =
      %{}
      |> require_string(params, "title")
      |> require_string(params, "author")
      |> check(params, "year", &(is_nil(&1) or is_integer(&1)), "must be an integer")
      |> check(params, "isbn", &(is_nil(&1) or is_binary(&1)), "must be a string")

    if errors == %{},
      do: {:ok, Map.take(params, ~w(title author year isbn))},
      else: {:error, errors}
  end

  defp require_string(errors, params, key) do
    case params[key] do
      v when is_binary(v) -> if String.trim(v) == "", do: Map.put(errors, key, "is required"), else: errors
      _ -> Map.put(errors, key, "is required")
    end
  end

  defp check(errors, params, key, fun, msg),
    do: if(fun.(params[key]), do: errors, else: Map.put(errors, key, msg))

  defp parse_id(id) do
    case Integer.parse(id) do
      {n, ""} -> {:ok, n}
      _ -> :error
    end
  end

  defp blank_to_nil(v) when v in [nil, ""], do: nil
  defp blank_to_nil(v), do: v

  defp not_found(conn), do: json(conn, 404, %{error: "book not found"})

  defp json(conn, status, body) do
    conn
    |> Plug.Conn.put_resp_content_type("application/json")
    |> Plug.Conn.send_resp(status, Jason.encode!(body))
  end
end
