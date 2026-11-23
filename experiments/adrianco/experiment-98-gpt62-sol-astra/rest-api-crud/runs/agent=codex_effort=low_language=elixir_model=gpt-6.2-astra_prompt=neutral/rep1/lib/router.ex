defmodule Books.Router do
  use Plug.Router
  alias Books.Store

  plug(:match)
  plug(:dispatch)

  get "/health" do
    json(conn, 200, %{status: "ok"})
  end

  get "/books" do
    author = fetch_query_params(conn).query_params["author"]
    json(conn, 200, Store.run({:list, author}))
  end

  post "/books" do
    write(conn, fn fields ->
      book = Store.run({:create, fields})
      conn |> put_resp_header("location", "/books/#{book["id"]}") |> json(201, book)
    end)
  end

  get "/books/:id" do
    result(conn, Store.run({:get, book_id(id)}))
  end

  put "/books/:id" do
    write(conn, fn fields -> result(conn, Store.run({{:replace, fields}, book_id(id)})) end)
  end

  delete "/books/:id" do
    result(conn, Store.run({:delete, book_id(id)}))
  end

  match _ do
    json(conn, 404, %{error: "Route not found"})
  end

  defp book_id(id) do
    case Integer.parse(id) do
      {n, ""} when n > 0 -> n
      _ -> :invalid
    end
  end

  defp write(conn, action) do
    case read_body(conn, length: 1_000_000) do
      {:ok, body, conn} ->
        case JSON.decode(body) do
          {:ok, fields} when is_map(fields) ->
            if valid?(fields) do
              action.(
                Map.merge(
                  %{"year" => nil, "isbn" => nil},
                  Map.take(fields, ~w(title author year isbn))
                )
              )
            else
              json(conn, 422, %{
                error: "Expected nonblank title and author, integer year and string isbn"
              })
            end

          _ ->
            json(conn, 400, %{error: "Expected a JSON object"})
        end

      {:more, _, conn} ->
        json(conn, 413, %{error: "Body too large"})

      {:error, _} ->
        json(conn, 400, %{error: "Unreadable body"})
    end
  end

  defp valid?(fields) do
    Enum.all?(~w(title author), fn key ->
      is_binary(fields[key]) and String.trim(fields[key]) != ""
    end) and
      (is_nil(fields["year"]) or is_integer(fields["year"])) and
      (is_nil(fields["isbn"]) or is_binary(fields["isbn"]))
  end

  defp result(conn, :missing), do: json(conn, 404, %{error: "Book not found"})
  defp result(conn, :ok), do: send_resp(conn, 204, "")
  defp result(conn, book), do: json(conn, 200, book)

  defp json(conn, status, data),
    do: conn |> put_resp_content_type("application/json") |> send_resp(status, JSON.encode!(data))
end
