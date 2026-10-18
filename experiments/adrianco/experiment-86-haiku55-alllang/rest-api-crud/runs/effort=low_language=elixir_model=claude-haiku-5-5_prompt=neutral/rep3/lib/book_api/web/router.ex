defmodule BookApi.Web.Router do
  @moduledoc "HTTP routes for the book collection API."
  use Plug.Router
  import Plug.Conn

  alias BookApi.Books

  plug(Plug.Logger)
  plug(:match)
  plug(Plug.Parsers, parsers: [:json], pass: ["application/json"], json_decoder: Jason)
  plug(:dispatch)

  get "/health" do
    json(conn, 200, %{status: "ok"})
  end

  post "/books" do
    case Books.create_book(body_params(conn)) do
      {:ok, book} -> json(conn, 201, serialize(book))
      {:error, changeset} -> json(conn, 422, errors(changeset))
    end
  end

  get "/books" do
    books = conn.query_params |> Books.list_books() |> Enum.map(&serialize/1)
    json(conn, 200, books)
  end

  get "/books/:id" do
    with {:ok, id} <- parse_id(id),
         %{} = book <- Books.get_book(id) do
      json(conn, 200, serialize(book))
    else
      _ -> not_found(conn)
    end
  end

  put "/books/:id" do
    with {:ok, id} <- parse_id(id),
         %{} = book <- Books.get_book(id) do
      case Books.update_book(book, body_params(conn)) do
        {:ok, book} -> json(conn, 200, serialize(book))
        {:error, changeset} -> json(conn, 422, errors(changeset))
      end
    else
      _ -> not_found(conn)
    end
  end

  delete "/books/:id" do
    with {:ok, id} <- parse_id(id),
         %{} = book <- Books.get_book(id) do
      {:ok, _} = Books.delete_book(book)
      send_resp(conn, 204, "")
    else
      _ -> not_found(conn)
    end
  end

  match _ do
    json(conn, 404, %{error: "not found"})
  end

  defp body_params(%{body_params: %Plug.Conn.Unfetched{}}), do: %{}
  defp body_params(%{body_params: params}) when is_map(params), do: params
  defp body_params(_), do: %{}

  defp parse_id(raw) do
    case Integer.parse(raw) do
      {id, ""} -> {:ok, id}
      _ -> :error
    end
  end

  defp not_found(conn), do: json(conn, 404, %{error: "book not found"})

  defp serialize(book) do
    %{
      id: book.id,
      title: book.title,
      author: book.author,
      year: book.year,
      isbn: book.isbn,
      inserted_at: book.inserted_at,
      updated_at: book.updated_at
    }
  end

  defp errors(changeset) do
    details =
      Ecto.Changeset.traverse_errors(changeset, fn {msg, opts} ->
        Regex.replace(~r"%{(\w+)}", msg, fn _, key ->
          opts |> Keyword.get(String.to_existing_atom(key), key) |> to_string()
        end)
      end)

    %{error: "validation failed", details: details}
  end

  defp json(conn, status, body) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(body))
  end
end
