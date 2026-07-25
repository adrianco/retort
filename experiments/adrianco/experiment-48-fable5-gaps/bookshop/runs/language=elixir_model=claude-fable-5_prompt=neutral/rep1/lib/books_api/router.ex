defmodule BooksApi.Router do
  use Plug.Router
  use Plug.ErrorHandler

  alias BooksApi.Books

  plug(Plug.Logger)
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
    conn = fetch_query_params(conn)

    filters =
      case conn.query_params["author"] do
        nil -> %{}
        author -> %{author: author}
      end

    send_json(conn, 200, Books.list_books(filters))
  end

  post "/books" do
    case Books.create_book(conn.body_params) do
      {:ok, book} -> send_json(conn, 201, book)
      {:error, changeset} -> send_validation_errors(conn, changeset)
    end
  end

  get "/books/:id" do
    with_book(conn, id, fn book -> send_json(conn, 200, book) end)
  end

  put "/books/:id" do
    with_book(conn, id, fn book ->
      case Books.update_book(book, conn.body_params) do
        {:ok, updated} -> send_json(conn, 200, updated)
        {:error, changeset} -> send_validation_errors(conn, changeset)
      end
    end)
  end

  delete "/books/:id" do
    with_book(conn, id, fn book ->
      {:ok, _} = Books.delete_book(book)
      send_resp(conn, 204, "")
    end)
  end

  match _ do
    send_json(conn, 404, %{error: "not found"})
  end

  @impl Plug.ErrorHandler
  def handle_errors(conn, %{kind: _kind, reason: _reason, stack: _stack}) do
    send_json(conn, conn.status || 500, %{error: "internal server error"})
  end

  defp with_book(conn, id, fun) do
    with {int_id, ""} <- Integer.parse(id),
         book when not is_nil(book) <- Books.get_book(int_id) do
      fun.(book)
    else
      _ -> send_json(conn, 404, %{error: "book not found"})
    end
  end

  defp send_validation_errors(conn, changeset) do
    errors =
      Ecto.Changeset.traverse_errors(changeset, fn {msg, opts} ->
        Enum.reduce(opts, msg, fn {key, value}, acc ->
          String.replace(acc, "%{#{key}}", to_string(value))
        end)
      end)

    send_json(conn, 422, %{errors: errors})
  end

  defp send_json(conn, status, body) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(body))
  end
end
