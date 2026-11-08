defmodule Books.Router do
  use Plug.Router
  import Ecto.Query
  alias Books.{Book, Repo}

  plug(:fetch_query_params)
  plug(:match)
  plug(Plug.Parsers, parsers: [:json], json_decoder: Jason)
  plug(:dispatch)

  get "/health" do
    json(conn, 200, %{status: "ok"})
  end

  get "/books" do
    query =
      case conn.query_params do
        %{"author" => author} when is_binary(author) ->
          from(b in Book, where: b.author == ^author)

        _ ->
          Book
      end

    json(conn, 200, Repo.all(from(b in query, order_by: b.id)) |> Enum.map(&serialize/1))
  end

  post "/books" do
    change(conn, %Book{}, 201)
  end

  get "/books/:id" do
    with_book(conn, id, fn book -> json(conn, 200, serialize(book)) end)
  end

  put "/books/:id" do
    with_book(conn, id, fn book -> change(conn, book, 200) end)
  end

  delete "/books/:id" do
    with_book(conn, id, fn book ->
      Repo.delete!(book)
      send_resp(conn, 204, "")
    end)
  end

  match _ do
    json(conn, 404, %{error: "Not found"})
  end

  defp with_book(conn, id, fun) do
    book =
      case Integer.parse(id) do
        {number, ""} when number > 0 -> Repo.get(Book, number)
        _ -> nil
      end

    if book, do: fun.(book), else: json(conn, 404, %{error: "Book not found"})
  end

  defp change(conn, book, status) do
    if is_map(conn.body_params) and not is_struct(conn.body_params) do
      save(conn, Book.changeset(book, conn.body_params), status)
    else
      json(conn, 400, %{error: "Expected a JSON object"})
    end
  end

  defp save(conn, changeset, status) do
    case Repo.insert_or_update(changeset) do
      {:ok, book} ->
        json(conn, status, serialize(book))

      {:error, changeset} ->
        errors =
          Ecto.Changeset.traverse_errors(changeset, fn {message, opts} ->
            Enum.reduce(opts, message, fn {key, value}, acc ->
              String.replace(acc, "%{#{key}}", to_string(value))
            end)
          end)

        json(conn, 422, %{errors: errors})
    end
  end

  defp serialize(book), do: Map.take(book, [:id, :title, :author, :year, :isbn])

  defp json(conn, status, body) do
    conn |> put_resp_content_type("application/json") |> send_resp(status, Jason.encode!(body))
  end

  def call(conn, opts) do
    super(conn, opts)
  rescue
    Plug.Parsers.ParseError -> json(conn, 400, %{error: "Invalid JSON"})
    Plug.Parsers.UnsupportedMediaTypeError -> json(conn, 415, %{error: "Unsupported media type"})
  end
end
