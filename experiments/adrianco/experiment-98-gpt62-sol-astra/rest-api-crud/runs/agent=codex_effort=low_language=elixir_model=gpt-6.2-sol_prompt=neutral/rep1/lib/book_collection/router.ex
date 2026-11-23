defmodule BookCollection.Router do
  use Plug.Router
  use Plug.ErrorHandler

  alias BookCollection.Store

  @max_integer 9_223_372_036_854_775_807
  @min_integer -9_223_372_036_854_775_808

  plug(:match)
  plug(:dispatch)

  get "/health" do
    case Store.health() do
      {:ok, _} -> json(conn, 200, %{status: "ok"})
      {:error, _} -> json(conn, 503, %{status: "unavailable"})
    end
  end

  get "/books" do
    conn = fetch_query_params(conn)

    case conn.query_params["author"] do
      author when is_binary(author) or is_nil(author) -> respond(conn, Store.list(author))
      _ -> json(conn, 400, %{error: "author must be a string"})
    end
  end

  post "/books" do
    write_book(conn, 201, &Store.create/1)
  end

  get "/books/:id" do
    with_id(conn, id, fn id -> respond(conn, Store.get(id)) end)
  end

  put "/books/:id" do
    with_id(conn, id, fn id -> write_book(conn, 200, &Store.update(id, &1)) end)
  end

  delete "/books/:id" do
    with_id(conn, id, fn id ->
      case Store.delete(id) do
        {:ok, _} -> send_resp(conn, 204, "")
        error -> respond(conn, error)
      end
    end)
  end

  match _ do
    json(conn, 404, %{error: "Not found"})
  end

  defp write_book(conn, status, save) do
    case read_body(conn, length: 64_000, read_length: 64_000) do
      {:ok, body, conn} ->
        with {:ok, %{} = attrs} <- JSON.decode(body),
             {:ok, fields} <- validate(attrs) do
          case save.(fields) do
            {:ok, book} ->
              conn =
                if status == 201,
                  do: put_resp_header(conn, "location", "/books/#{book.id}"),
                  else: conn

              json(conn, status, book)

            error ->
              respond(conn, error)
          end
        else
          {:invalid, errors} -> json(conn, 422, %{errors: errors})
          _ -> json(conn, 400, %{error: "Expected a JSON object"})
        end

      {:more, _, conn} ->
        json(conn, 413, %{error: "Request body too large"})

      {:error, _} ->
        json(conn, 400, %{error: "Could not read request body"})
    end
  end

  defp validate(attrs) do
    title = trim(attrs["title"])
    author = trim(attrs["author"])
    year = attrs["year"]
    isbn = attrs["isbn"]

    checks = [
      {"title", is_binary(title) and title != "", "must be a nonblank string"},
      {"author", is_binary(author) and author != "", "must be a nonblank string"},
      {"year", is_nil(year) or (is_integer(year) and year in @min_integer..@max_integer),
       "must be an integer in the SQLite range"},
      {"isbn", is_nil(isbn) or is_binary(isbn), "must be a string"}
    ]

    errors = for {field, false, message} <- checks, into: %{}, do: {field, message}
    if map_size(errors) == 0, do: {:ok, [title, author, year, isbn]}, else: {:invalid, errors}
  end

  defp trim(value) when is_binary(value), do: String.trim(value)
  defp trim(value), do: value

  defp with_id(conn, value, action) do
    case Integer.parse(value) do
      {id, ""} when id in 1..@max_integer -> action.(id)
      _ -> json(conn, 400, %{error: "Invalid book ID"})
    end
  end

  defp respond(conn, {:ok, data}), do: json(conn, 200, data)
  defp respond(conn, {:error, :not_found}), do: json(conn, 404, %{error: "Book not found"})
  defp respond(conn, {:error, _}), do: json(conn, 500, %{error: "Database request failed"})

  @impl Plug.ErrorHandler
  def handle_errors(conn, _error) do
    error = if conn.status < 500, do: "Invalid request", else: "Internal server error"
    json(conn, conn.status, %{error: error})
  end

  defp json(conn, status, data) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, JSON.encode!(data))
  end
end
