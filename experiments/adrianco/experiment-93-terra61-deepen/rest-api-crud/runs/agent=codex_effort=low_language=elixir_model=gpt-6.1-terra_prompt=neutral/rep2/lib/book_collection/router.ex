defmodule BookCollection.Router do
  use Plug.Router
  import Ecto.Query
  alias BookCollection.{Book, Repo}

  plug :match
  plug :parse_json
  plug :dispatch

  get "/health" do
    json(conn, 200, %{status: "ok"})
  end

  get "/books" do
    conn = fetch_query_params(conn)
    query = case conn.query_params["author"] do
      nil -> Book
      author -> from b in Book, where: b.author == ^author
    end
    books = query |> order_by([b], asc: b.id) |> Repo.all() |> Enum.map(&Book.json/1)
    json(conn, 200, books)
  end

  post "/books" do
    save(conn, %Book{}, 201)
  end

  get "/books/:id" do
    with_book(conn, id, fn book -> json(conn, 200, Book.json(book)) end)
  end

  put "/books/:id" do
    with_book(conn, id, fn book -> save(conn, book, 200) end)
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

  defp parse_json(conn, _opts) do
    Plug.Parsers.call(conn, Plug.Parsers.init(parsers: [:json], json_decoder: Jason))
  rescue
    Plug.Parsers.ParseError -> conn |> json(400, %{error: "Invalid JSON"}) |> halt()
  end

  defp with_book(conn, id, fun) do
    book = case Integer.parse(id) do
      {number, ""} when number > 0 -> Repo.get(Book, number)
      _ -> nil
    end
    if book, do: fun.(book), else: json(conn, 404, %{error: "Book not found"})
  end

  defp save(conn, book, status) do
    case Book.changeset(book, conn.body_params) |> Repo.insert_or_update() do
      {:ok, saved} -> json(conn, status, Book.json(saved))
      {:error, changeset} ->
        errors = Ecto.Changeset.traverse_errors(changeset, fn {message, _opts} -> message end)
        json(conn, 422, %{errors: errors})
    end
  end

  defp json(conn, status, data) do
    conn |> put_resp_content_type("application/json") |> send_resp(status, Jason.encode!(data))
  end
end
