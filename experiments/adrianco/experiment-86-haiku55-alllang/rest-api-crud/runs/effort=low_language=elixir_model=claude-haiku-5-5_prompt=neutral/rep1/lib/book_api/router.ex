defmodule BookApi.Router do
  @moduledoc "HTTP interface for the book collection."
  use Plug.Router

  alias BookApi.{Books, DB}

  plug :match

  plug :parse_body

  plug :dispatch

  get "/health" do
    case DB.query("SELECT 1") do
      {:ok, _} -> json(conn, 200, %{status: "ok"})
      {:error, _} -> json(conn, 503, %{status: "unavailable"})
    end
  end

  post "/books" do
    respond(Books.create(conn.body_params), conn, 201)
  end

  get "/books" do
    conn = fetch_query_params(conn)
    respond(Books.list(conn.query_params), conn, 200)
  end

  get "/books/:id" do
    respond(with_id(id, &Books.get/1), conn, 200)
  end

  put "/books/:id" do
    respond(with_id(id, &Books.update(&1, conn.body_params)), conn, 200)
  end

  delete "/books/:id" do
    case with_id(id, &Books.delete/1) do
      :ok -> send_resp(conn, 204, "")
      error -> respond(error, conn, 204)
    end
  end

  match _ do
    json(conn, 404, %{error: "not_found"})
  end

  defp respond({:ok, body}, conn, status), do: json(conn, status, body)
  defp respond({:error, :not_found}, conn, _), do: json(conn, 404, %{error: "not_found"})

  defp respond({:error, {:validation, details}}, conn, _) do
    json(conn, 422, %{error: "validation_failed", details: details})
  end

  defp respond({:error, _reason}, conn, _), do: json(conn, 500, %{error: "internal_error"})

  defp with_id(raw, fun) do
    case Integer.parse(raw) do
      {id, ""} -> fun.(id)
      _ -> {:error, :not_found}
    end
  end

  defp json(conn, status, body) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(body))
  end

  defp parse_body(conn, _opts) do
    Plug.Parsers.call(conn, Plug.Parsers.init(parsers: [:json], pass: ["*/*"], json_decoder: Jason))
  rescue
    Plug.Parsers.ParseError -> conn |> json(400, %{error: "invalid_json"}) |> halt()
  end
end
