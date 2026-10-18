defmodule BookApi.Router do
  use Plug.Router

  plug(Plug.Logger)
  plug(Plug.Parsers, parsers: [:json], pass: ["application/json"], json_decoder: Jason)
  plug(:match)
  plug(:dispatch)

  get "/health" do
    send_json(conn, 200, %{"status" => "ok"})
  end

  get "/books" do
    case BookApi.Store.list(conn.params["author"]) do
      {:ok, books} -> send_json(conn, 200, books)
      _ -> send_json(conn, 500, %{"error" => "database error"})
    end
  end

  post "/books" do
    with :ok <- validate(conn.body_params),
         {:ok, book} <- BookApi.Store.create(conn.body_params) do
      send_json(conn, 201, book)
    else
      {:error, message} -> send_json(conn, 400, %{"error" => message})
      _ -> send_json(conn, 500, %{"error" => "database error"})
    end
  end

  get "/books/:id" do
    case parse_id(id) do
      {:ok, parsed_id} -> respond_book(conn, BookApi.Store.get(parsed_id))
      {:error, message} -> send_json(conn, 400, %{"error" => message})
    end
  end

  put "/books/:id" do
    with {:ok, id} <- parse_id(id),
         :ok <- validate(conn.body_params),
         result <- BookApi.Store.update(id, conn.body_params) do
      respond_book(conn, result)
    else
      {:error, message} -> send_json(conn, 400, %{"error" => message})
    end
  end

  delete "/books/:id" do
    case parse_id(id) do
      {:ok, parsed_id} -> respond_book(conn, BookApi.Store.delete(parsed_id))
      _ -> send_json(conn, 400, %{"error" => "id must be a positive integer"})
    end
  end

  match _ do
    send_json(conn, 404, %{"error" => "not found"})
  end

  defp validate(attrs) when is_map(attrs) do
    if nonblank?(attrs["title"]) and nonblank?(attrs["author"]),
      do: :ok,
      else: {:error, "title and author are required"}
  end

  defp validate(_), do: {:error, "request body must be a JSON object"}
  defp nonblank?(value), do: is_binary(value) and String.trim(value) != ""

  defp parse_id(id) do
    case Integer.parse(id) do
      {value, ""} when value > 0 -> {:ok, value}
      _ -> {:error, "id must be a positive integer"}
    end
  end

  defp respond_book(conn, {:ok, book}), do: send_json(conn, 200, book)
  defp respond_book(conn, :not_found), do: send_json(conn, 404, %{"error" => "book not found"})
  defp respond_book(conn, _), do: send_json(conn, 500, %{"error" => "database error"})

  defp send_json(conn, status, body) do
    conn
    |> Plug.Conn.put_resp_content_type("application/json")
    |> Plug.Conn.send_resp(status, Jason.encode!(body))
  end
end
