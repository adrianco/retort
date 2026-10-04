defmodule BookApi.Store do
  @moduledoc """
  SQLite-backed storage for books. A single process owns the connection and
  serialises access to it.
  """
  use GenServer

  alias Exqlite.Sqlite3

  @columns "id, title, author, year, isbn"

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: Keyword.get(opts, :name, __MODULE__))
  end

  @doc "Lists books, optionally restricted to an exact (case-insensitive) author."
  def list(author \\ nil)

  def list(nil), do: query("SELECT #{@columns} FROM books ORDER BY id", [])

  def list(author) do
    query("SELECT #{@columns} FROM books WHERE author = ?1 COLLATE NOCASE ORDER BY id", [author])
  end

  def get(id) do
    one(query("SELECT #{@columns} FROM books WHERE id = ?1", [id]))
  end

  def create(attrs) do
    one(
      query(
        "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4) RETURNING #{@columns}",
        [attrs.title, attrs.author, attrs.year, attrs.isbn]
      )
    )
  end

  def update(id, attrs) do
    one(
      query(
        "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5 RETURNING #{@columns}",
        [attrs.title, attrs.author, attrs.year, attrs.isbn, id]
      )
    )
  end

  def delete(id) do
    case query("DELETE FROM books WHERE id = ?1 RETURNING id", [id]) do
      [] -> {:error, :not_found}
      [_] -> :ok
    end
  end

  @doc "Removes every book. Intended for tests."
  def delete_all do
    query("DELETE FROM books RETURNING id", [])
    :ok
  end

  defp one([]), do: {:error, :not_found}
  defp one([book]), do: {:ok, book}

  defp query(sql, params), do: GenServer.call(__MODULE__, {:query, sql, params})

  @impl true
  def init(opts) do
    {:ok, conn} = Sqlite3.open(Keyword.fetch!(opts, :database))

    :ok =
      Sqlite3.execute(conn, """
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
      """)

    {:ok, conn}
  end

  @impl true
  def handle_call({:query, sql, params}, _from, conn) do
    {:ok, stmt} = Sqlite3.prepare(conn, sql)

    try do
      :ok = Sqlite3.bind(stmt, params)
      {:ok, rows} = Sqlite3.fetch_all(conn, stmt)
      {:reply, Enum.map(rows, &to_book/1), conn}
    after
      Sqlite3.release(conn, stmt)
    end
  end

  defp to_book([id]), do: %{id: id}

  defp to_book([id, title, author, year, isbn]) do
    %{id: id, title: title, author: author, year: year, isbn: isbn}
  end
end
