defmodule Books.Repo do
  @moduledoc "SQLite-backed storage; a GenServer serializes access to one connection."
  use GenServer
  alias Exqlite.Sqlite3

  @cols "id, title, author, year, isbn"

  def start_link(path), do: GenServer.start_link(__MODULE__, path, name: __MODULE__)

  def list(author \\ nil), do: GenServer.call(__MODULE__, {:list, author})
  def get(id), do: GenServer.call(__MODULE__, {:get, id})
  def create(attrs), do: GenServer.call(__MODULE__, {:create, attrs})
  def update(id, attrs), do: GenServer.call(__MODULE__, {:update, id, attrs})
  def delete(id), do: GenServer.call(__MODULE__, {:delete, id})
  def reset, do: GenServer.call(__MODULE__, :reset)

  @impl true
  def init(path) do
    {:ok, conn} = Sqlite3.open(path)

    :ok =
      Sqlite3.execute(conn, """
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)
      """)

    {:ok, conn}
  end

  @impl true
  def handle_call({:list, nil}, _, c), do: {:reply, query(c, "SELECT #{@cols} FROM books ORDER BY id", []), c}
  def handle_call({:list, a}, _, c), do: {:reply, query(c, "SELECT #{@cols} FROM books WHERE author = ?1 ORDER BY id", [a]), c}
  def handle_call({:get, id}, _, c), do: {:reply, fetch(c, id), c}

  def handle_call({:create, b}, _, c) do
    query(c, "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)", [b["title"], b["author"], b["year"], b["isbn"]])
    {:ok, id} = Sqlite3.last_insert_rowid(c)
    {:reply, fetch(c, id), c}
  end

  def handle_call({:update, id, b}, _, c) do
    case fetch(c, id) do
      nil -> {:reply, nil, c}
      _ ->
        query(c, "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5", [b["title"], b["author"], b["year"], b["isbn"], id])
        {:reply, fetch(c, id), c}
    end
  end

  def handle_call({:delete, id}, _, c) do
    case fetch(c, id) do
      nil -> {:reply, false, c}
      _ -> query(c, "DELETE FROM books WHERE id = ?1", [id]); {:reply, true, c}
    end
  end

  def handle_call(:reset, _, c), do: {:reply, Sqlite3.execute(c, "DELETE FROM books"), c}

  defp fetch(c, id), do: c |> query("SELECT #{@cols} FROM books WHERE id = ?1", [id]) |> List.first()

  defp query(conn, sql, params) do
    {:ok, stmt} = Sqlite3.prepare(conn, sql)
    :ok = Sqlite3.bind(stmt, params)
    {:ok, rows} = Sqlite3.fetch_all(conn, stmt)
    :ok = Sqlite3.release(conn, stmt)

    Enum.map(rows, fn [id, t, a, y, i] -> %{id: id, title: t, author: a, year: y, isbn: i} end)
  end
end
