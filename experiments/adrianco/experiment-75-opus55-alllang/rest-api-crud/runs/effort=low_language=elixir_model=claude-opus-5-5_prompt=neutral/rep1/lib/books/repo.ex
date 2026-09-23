defmodule Books.Repo do
  @moduledoc "SQLite-backed storage for books, serialized through a GenServer."
  use GenServer
  alias Exqlite.Sqlite3

  @fields ~w(title author year isbn)

  def start_link(path), do: GenServer.start_link(__MODULE__, path, name: __MODULE__)

  def list(author \\ nil), do: GenServer.call(__MODULE__, {:list, author})
  def get(id), do: GenServer.call(__MODULE__, {:get, id})
  def create(attrs), do: GenServer.call(__MODULE__, {:create, attrs})
  def update(id, attrs), do: GenServer.call(__MODULE__, {:update, id, attrs})
  def delete(id), do: GenServer.call(__MODULE__, {:delete, id})
  def reset, do: GenServer.call(__MODULE__, :reset)

  @impl true
  def init(path) do
    {:ok, db} = Sqlite3.open(path)

    :ok =
      Sqlite3.execute(db, """
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)
      """)

    {:ok, db}
  end

  @impl true
  def handle_call({:list, nil}, _, db), do: {:reply, query(db, "SELECT * FROM books ORDER BY id", []), db}

  def handle_call({:list, author}, _, db),
    do: {:reply, query(db, "SELECT * FROM books WHERE author = ?1 ORDER BY id", [author]), db}

  def handle_call({:get, id}, _, db), do: {:reply, fetch(db, id), db}

  def handle_call({:create, a}, _, db) do
    query(db, "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)", values(a))
    {:ok, id} = Sqlite3.last_insert_rowid(db)
    {:reply, fetch(db, id), db}
  end

  def handle_call({:update, id, a}, _, db) do
    case fetch(db, id) do
      {:ok, _} ->
        query(db, "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5", values(a) ++ [id])
        {:reply, fetch(db, id), db}

      err ->
        {:reply, err, db}
    end
  end

  def handle_call({:delete, id}, _, db) do
    case fetch(db, id) do
      {:ok, _} ->
        query(db, "DELETE FROM books WHERE id = ?1", [id])
        {:reply, :ok, db}

      err ->
        {:reply, err, db}
    end
  end

  def handle_call(:reset, _, db), do: {:reply, Sqlite3.execute(db, "DELETE FROM books"), db}

  defp values(a), do: Enum.map(@fields, &Map.get(a, &1))

  defp fetch(db, id) do
    case query(db, "SELECT * FROM books WHERE id = ?1", [id]) do
      [book] -> {:ok, book}
      [] -> {:error, :not_found}
    end
  end

  defp query(db, sql, params) do
    {:ok, stmt} = Sqlite3.prepare(db, sql)
    :ok = Sqlite3.bind(stmt, params)
    {:ok, cols} = Sqlite3.columns(db, stmt)
    {:ok, rows} = Sqlite3.fetch_all(db, stmt)
    :ok = Sqlite3.release(db, stmt)
    Enum.map(rows, fn row -> Map.new(Enum.zip(cols, row)) end)
  end
end
