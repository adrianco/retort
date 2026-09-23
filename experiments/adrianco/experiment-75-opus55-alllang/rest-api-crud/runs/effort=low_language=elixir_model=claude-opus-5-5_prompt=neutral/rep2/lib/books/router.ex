defmodule Books.Router do
  use Plug.Router

  plug Plug.Parsers, parsers: [:json], pass: ["*/*"], json_decoder: Jason
  plug :match
  plug :dispatch

  get "/health", do: json(conn, 200, %{status: "ok"})

  get "/books" do
    conn = Plug.Conn.fetch_query_params(conn)
    json(conn, 200, Books.Repo.list(conn.query_params["author"]))
  end

  post "/books" do
    with {:ok, attrs} <- validate(conn.body_params) do
      json(conn, 201, Books.Repo.create(attrs))
    else
      {:error, errs} -> json(conn, 422, %{errors: errs})
    end
  end

  get "/books/:id" do
    with {:ok, id} <- parse_id(id), %{} = book <- Books.Repo.get(id) do
      json(conn, 200, book)
    else
      _ -> not_found(conn)
    end
  end

  put "/books/:id" do
    with {:ok, id} <- parse_id(id), {:ok, attrs} <- validate(conn.body_params) do
      case Books.Repo.update(id, attrs) do
        nil -> not_found(conn)
        book -> json(conn, 200, book)
      end
    else
      {:error, errs} -> json(conn, 422, %{errors: errs})
      :error -> not_found(conn)
    end
  end

  delete "/books/:id" do
    with {:ok, id} <- parse_id(id), true <- Books.Repo.delete(id) do
      send_resp(conn, 204, "")
    else
      _ -> not_found(conn)
    end
  end

  match _, do: not_found(conn)

  @doc false
  def validate(params) when is_map(params) do
    errs =
      []
      |> req(params, "title")
      |> req(params, "author")
      |> then(fn e -> if valid_year?(params["year"]), do: e, else: ["year must be an integer" | e] end)
      |> then(fn e -> if is_nil(params["isbn"]) or is_binary(params["isbn"]), do: e, else: ["isbn must be a string" | e] end)

    if errs == [], do: {:ok, Map.take(params, ~w(title author year isbn))}, else: {:error, Enum.reverse(errs)}
  end

  defp req(errs, p, k) do
    case p[k] do
      v when is_binary(v) -> if String.trim(v) == "", do: ["#{k} is required" | errs], else: errs
      _ -> ["#{k} is required" | errs]
    end
  end

  defp valid_year?(y), do: is_nil(y) or is_integer(y)

  defp parse_id(id) do
    case Integer.parse(id) do
      {n, ""} -> {:ok, n}
      _ -> :error
    end
  end

  defp not_found(conn), do: json(conn, 404, %{error: "not found"})

  defp json(conn, status, body) do
    conn |> put_resp_content_type("application/json") |> send_resp(status, Jason.encode!(body))
  end
end
