defmodule BookApi.Store do
  @moduledoc """
  SQLite-backed storage for books.

  A single GenServer owns the database connection, so all statements are
  serialized through it.
  """
  use GenServer

  alias Exqlite.Sqlite3

  @columns "id, title, author, year, isbn"

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: Keyword.get(opts, :name, __MODULE__))
  end

  @doc "Inserts a book and returns it with its generated id."
  def create(attrs), do: GenServer.call(__MODULE__, {:create, attrs})

  @doc "Lists all books, optionally only those by `author` (case-insensitive exact match)."
  def list(author \\ nil), do: GenServer.call(__MODULE__, {:list, author})

  @doc "Returns `{:ok, book}` or `:error` when no book has the given id."
  def get(id), do: GenServer.call(__MODULE__, {:get, id})

  @doc "Replaces a book's attributes. Returns `{:ok, book}` or `:error` when missing."
  def update(id, attrs), do: GenServer.call(__MODULE__, {:update, id, attrs})

  @doc "Deletes a book. Returns `:ok` or `:error` when missing."
  def delete(id), do: GenServer.call(__MODULE__, {:delete, id})

  @doc "Removes every book."
  def delete_all, do: GenServer.call(__MODULE__, :delete_all)

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
  def handle_call({:create, attrs}, _from, conn) do
    query(conn, "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)", [
      attrs.title,
      attrs.author,
      attrs.year,
      attrs.isbn
    ])

    {:ok, id} = Sqlite3.last_insert_rowid(conn)
    {:reply, Map.put(attrs, :id, id), conn}
  end

  def handle_call({:list, nil}, _from, conn) do
    {:reply, select(conn, "SELECT #{@columns} FROM books ORDER BY id", []), conn}
  end

  def handle_call({:list, author}, _from, conn) do
    sql = "SELECT #{@columns} FROM books WHERE author = ?1 COLLATE NOCASE ORDER BY id"
    {:reply, select(conn, sql, [author]), conn}
  end

  def handle_call({:get, id}, _from, conn) do
    {:reply, fetch(conn, id), conn}
  end

  def handle_call({:update, id, attrs}, _from, conn) do
    query(conn, "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5", [
      attrs.title,
      attrs.author,
      attrs.year,
      attrs.isbn,
      id
    ])

    {:reply, fetch(conn, id), conn}
  end

  def handle_call({:delete, id}, _from, conn) do
    query(conn, "DELETE FROM books WHERE id = ?1", [id])
    {:ok, changes} = Sqlite3.changes(conn)
    {:reply, if(changes > 0, do: :ok, else: :error), conn}
  end

  def handle_call(:delete_all, _from, conn) do
    query(conn, "DELETE FROM books", [])
    {:reply, :ok, conn}
  end

  defp fetch(conn, id) do
    case select(conn, "SELECT #{@columns} FROM books WHERE id = ?1", [id]) do
      [book] -> {:ok, book}
      [] -> :error
    end
  end

  defp select(conn, sql, args) do
    conn
    |> query(sql, args)
    |> Enum.map(fn [id, title, author, year, isbn] ->
      %{id: id, title: title, author: author, year: year, isbn: isbn}
    end)
  end

  defp query(conn, sql, args) do
    {:ok, stmt} = Sqlite3.prepare(conn, sql)

    try do
      :ok = Sqlite3.bind(stmt, args)
      {:ok, rows} = Sqlite3.fetch_all(conn, stmt)
      rows
    after
      Sqlite3.release(conn, stmt)
    end
  end
end
