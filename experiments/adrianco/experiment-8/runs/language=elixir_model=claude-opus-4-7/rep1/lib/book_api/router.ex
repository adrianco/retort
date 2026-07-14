defmodule BookApi.Router do
  @moduledoc "HTTP router for the books REST API."

  use Plug.Router

  alias BookApi.Books

  plug(:match)

  plug(Plug.Parsers,
    parsers: [:json],
    pass: ["application/json"],
    json_decoder: Jason
  )

  plug(:dispatch)

  get "/health" do
    send_json(conn, 200, %{status: "ok"})
  end

  get "/books" do
    conn = Plug.Conn.fetch_query_params(conn)
    filters = Map.take(conn.query_params, ["author"])
    books = Books.list(filters)
    send_json(conn, 200, books)
  end

  get "/books/:id" do
    case Books.get(id) do
      {:ok, book} -> send_json(conn, 200, book)
      {:error, :not_found} -> send_json(conn, 404, %{error: "book not found"})
    end
  end

  post "/books" do
    case Books.create(conn.body_params) do
      {:ok, book} ->
        send_json(conn, 201, book)

      {:error, {:validation, errors}} ->
        send_json(conn, 422, %{errors: errors})
    end
  end

  put "/books/:id" do
    case Books.update(id, conn.body_params) do
      {:ok, book} ->
        send_json(conn, 200, book)

      {:error, :not_found} ->
        send_json(conn, 404, %{error: "book not found"})

      {:error, {:validation, errors}} ->
        send_json(conn, 422, %{errors: errors})
    end
  end

  delete "/books/:id" do
    case Books.delete(id) do
      :ok -> send_resp(conn, 204, "")
      {:error, :not_found} -> send_json(conn, 404, %{error: "book not found"})
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
end
