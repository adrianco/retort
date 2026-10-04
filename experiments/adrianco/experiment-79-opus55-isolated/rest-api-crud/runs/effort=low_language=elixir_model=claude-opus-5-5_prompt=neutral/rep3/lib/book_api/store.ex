defmodule BookApi.Store do
  @moduledoc """
  SQLite-backed book storage. A single GenServer owns the database
  connection and serializes all access to it.
  """
  use GenServer

  alias Exqlite.Sqlite3

  @columns ~w(id title author year isbn)a
  @select "SELECT id, title, author, year, isbn FROM books"

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: Keyword.get(opts, :name, __MODULE__))
  end

  @doc "Lists books, optionally restricted to an exact author match."
  def list(author \\ nil), do: GenServer.call(__MODULE__, {:list, author})

  def get(id), do: GenServer.call(__MODULE__, {:get, id})

  def create(attrs), do: GenServer.call(__MODULE__, {:create, attrs})

  def update(id, attrs), do: GenServer.call(__MODULE__, {:update, id, attrs})

  def delete(id), do: GenServer.call(__MODULE__, {:delete, id})

  @doc "Removes every book. Intended for tests."
  def clear, do: GenServer.call(__MODULE__, :clear)

  @impl true
  def init(opts) do
    {:ok, conn} = Sqlite3.open(Keyword.fetch!(opts, :path))

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
  def handle_call({:list, nil}, _from, conn) do
    {:reply, query(conn, @select <> " ORDER BY id", []), conn}
  end

  def handle_call({:list, author}, _from, conn) do
    {:reply, query(conn, @select <> " WHERE author = ?1 ORDER BY id", [author]), conn}
  end

  def handle_call({:get, id}, _from, conn) do
    {:reply, fetch(conn, id), conn}
  end

  def handle_call({:create, attrs}, _from, conn) do
    query(conn, "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)", [
      attrs.title,
      attrs.author,
      attrs.year,
      attrs.isbn
    ])

    {:ok, id} = Sqlite3.last_insert_rowid(conn)
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
    {:reply, if(changes > 0, do: :ok, else: {:error, :not_found}), conn}
  end

  def handle_call(:clear, _from, conn) do
    query(conn, "DELETE FROM books", [])
    {:reply, :ok, conn}
  end

  defp fetch(conn, id) do
    case query(conn, @select <> " WHERE id = ?1", [id]) do
      [book] -> {:ok, book}
      [] -> {:error, :not_found}
    end
  end

  defp query(conn, sql, params) do
    {:ok, stmt} = Sqlite3.prepare(conn, sql)

    try do
      :ok = Sqlite3.bind(stmt, params)
      {:ok, rows} = Sqlite3.fetch_all(conn, stmt)
      Enum.map(rows, &(@columns |> Enum.zip(&1) |> Map.new()))
    after
      Sqlite3.release(conn, stmt)
    end
  end
end
