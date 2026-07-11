defmodule BookApi.Router do
  use Plug.Router
  import Ecto.Query
  import Plug.Conn

  alias BookApi.Repo
  alias BookApi.Books.Book

  plug(:match)
  plug(Plug.Parsers,
    parsers: [:json],
    json_decoder: Jason,
    length: 1_048_576
  )
  plug(:dispatch)

  defp json(conn, map) do
    conn
    |> put_resp_content_type("application/json")
    |> resp(200, Jason.encode!(map))
  end

  # Health check endpoint
  get "/health" do
    conn
    |> put_status(200)
    |> json(%{status: "healthy"})
  end

  # POST /books - Create a new book
  post "/books" do
    params = conn.params

    changeset =
      %Book{}
      |> Book.changeset(params)

    case Repo.insert(changeset) do
      {:ok, book} ->
        conn
        |> put_status(201)
        |> json(%{
          id: book.id,
          title: book.title,
          author: book.author,
          year: book.year,
          isbn: book.isbn
        })

      {:error, changeset} ->
        errors = Ecto.Changeset.traverse_errors(changeset, fn {msg, _}, _ -> msg end)
        conn
        |> put_status(400)
        |> json(%{error: "Validation failed", details: errors})
    end
  end

  # GET /books - List all books, optionally filtered by author
  get "/books" do
    query = from(b in Book, order_by: [asc: b.id])
    query = maybe_filter_by_author(query, conn.params["author"])
    books = Repo.all(query)

    conn
    |> put_status(200)
    |> json(%{books: books})
  end

  # GET /books/:id - Get a single book
  get "/books/:id" do
    case Repo.get(Book, String.to_integer(id)) do
      nil ->
        conn
        |> put_status(404)
        |> json(%{error: "Book not found"})

      book ->
        conn
        |> put_status(200)
        |> json(%{
          id: book.id,
          title: book.title,
          author: book.author,
          year: book.year,
          isbn: book.isbn
        })
    end
  end

  # PUT /books/:id - Update a book
  put "/books/:id" do
    case Repo.get(Book, String.to_integer(id)) do
      nil ->
        conn
        |> put_status(404)
        |> json(%{error: "Book not found"})

      book ->
        changeset =
          book
          |> Book.changeset(conn.params)

        case Repo.update(changeset) do
          {:ok, book} ->
            conn
            |> put_status(200)
            |> json(%{
              id: book.id,
              title: book.title,
              author: book.author,
              year: book.year,
              isbn: book.isbn
            })

          {:error, changeset} ->
            errors = Ecto.Changeset.traverse_errors(changeset, fn {msg, _}, _ -> msg end)
            conn
            |> put_status(400)
            |> json(%{error: "Validation failed", details: errors})
        end
    end
  end

  # DELETE /books/:id - Delete a book
  delete "/books/:id" do
    case Repo.get(Book, String.to_integer(id)) do
      nil ->
        conn
        |> put_status(404)
        |> json(%{error: "Book not found"})

      book ->
        {:ok, _} = Repo.delete(book)

        conn
        |> put_status(200)
        |> json(%{message: "Book deleted"})
    end
  end

  match _ do
    conn
    |> put_status(404)
    |> json(%{error: "Not found"})
  end

  defp maybe_filter_by_author(query, nil), do: query

  defp maybe_filter_by_author(query, author) when is_binary(author) do
    author_pattern = String.downcase(author)
    from(q in query, where: ilike(q.author, ^author_pattern))
  end
end
