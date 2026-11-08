defmodule Books.Router do
  use Plug.Router

  plug(:match)
  plug(:parse_body)
  plug(:dispatch)

  defp parse_body(conn, _) do
    Plug.Parsers.call(
      conn,
      Plug.Parsers.init(parsers: [:json], pass: ["application/json"], json_decoder: Jason)
    )
  rescue
    Plug.Parsers.ParseError ->
      json(conn, 400, %{error: "Invalid JSON"}) |> halt()

    Plug.Parsers.UnsupportedMediaTypeError ->
      json(conn, 415, %{error: "Unsupported media type"}) |> halt()
  end

  get "/health" do
    json(conn, 200, %{status: "ok"})
  end

  get "/books" do
    conn = fetch_query_params(conn)
    json(conn, 200, Books.Store.list(conn.query_params["author"]))
  end

  get "/books/:id" do
    with_id(conn, id, fn id ->
      case Books.Store.get(id) do
        nil -> not_found(conn)
        book -> json(conn, 200, book)
      end
    end)
  end

  post "/books" do
    case validate(conn.body_params) do
      {:ok, attrs} ->
        book = Books.Store.create(attrs)
        conn |> put_resp_header("location", "/books/#{book.id}") |> json(201, book)

      {:error, errors} ->
        json(conn, 422, %{errors: errors})
    end
  end

  put "/books/:id" do
    with_id(conn, id, fn id ->
      if Books.Store.get(id) do
        case validate(conn.body_params) do
          {:ok, attrs} ->
            case Books.Store.update(id, attrs) do
              nil -> not_found(conn)
              book -> json(conn, 200, book)
            end

          {:error, errors} ->
            json(conn, 422, %{errors: errors})
        end
      else
        not_found(conn)
      end
    end)
  end

  delete "/books/:id" do
    with_id(conn, id, fn id ->
      if Books.Store.delete(id), do: send_resp(conn, 204, ""), else: not_found(conn)
    end)
  end

  match(_, do: not_found(conn))

  defp validate(attrs) when is_map(attrs) and not is_struct(attrs) do
    errors =
      Enum.reduce(["title", "author"], %{}, fn key, errors ->
        value = attrs[key]

        if is_binary(value) and String.trim(value) != "",
          do: errors,
          else: Map.put(errors, key, "is required and must be a non-empty string")
      end)

    errors =
      if is_nil(attrs["year"]) or
           (is_integer(attrs["year"]) and attrs["year"] >= -9_223_372_036_854_775_808 and
              attrs["year"] <= 9_223_372_036_854_775_807),
         do: errors,
         else: Map.put(errors, "year", "must be an integer")

    errors =
      if is_nil(attrs["isbn"]) or is_binary(attrs["isbn"]),
        do: errors,
        else: Map.put(errors, "isbn", "must be a string")

    if map_size(errors) == 0, do: {:ok, attrs}, else: {:error, errors}
  end

  defp validate(_), do: {:error, %{body: "must be a JSON object"}}

  defp with_id(conn, id, fun) do
    case Integer.parse(id) do
      {number, ""} when number > 0 and number <= 9_223_372_036_854_775_807 -> fun.(number)
      _ -> not_found(conn)
    end
  end

  defp not_found(conn), do: json(conn, 404, %{error: "Not found"})

  defp json(conn, status, data),
    do:
      conn |> put_resp_content_type("application/json") |> send_resp(status, Jason.encode!(data))
end
