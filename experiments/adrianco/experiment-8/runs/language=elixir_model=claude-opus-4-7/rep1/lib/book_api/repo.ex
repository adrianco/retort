defmodule BookApi.Repo do
  @moduledoc """
  Wraps a single Exqlite connection with simple query helpers, runs migrations on start,
  and serializes access through a GenServer so SQLite writes don't collide.
  """

  use GenServer

  alias Exqlite.Sqlite3

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def query(sql, params \\ []) do
    GenServer.call(__MODULE__, {:query, sql, params})
  end

  def execute(sql, params \\ []) do
    GenServer.call(__MODULE__, {:execute, sql, params})
  end

  def last_insert_rowid do
    GenServer.call(__MODULE__, :last_insert_rowid)
  end

  def reset! do
    GenServer.call(__MODULE__, :reset)
  end

  @impl true
  def init(opts) do
    db_path = Keyword.fetch!(opts, :db_path)
    {:ok, conn} = Sqlite3.open(db_path)
    :ok = ensure_schema(conn)
    {:ok, %{conn: conn, db_path: db_path}}
  end

  @impl true
  def handle_call({:query, sql, params}, _from, %{conn: conn} = state) do
    {:reply, do_query(conn, sql, params), state}
  end

  def handle_call({:execute, sql, params}, _from, %{conn: conn} = state) do
    {:reply, do_execute(conn, sql, params), state}
  end

  def handle_call(:last_insert_rowid, _from, %{conn: conn} = state) do
    {:reply, do_last_insert_rowid(conn), state}
  end

  def handle_call(:reset, _from, %{conn: conn} = state) do
    :ok = do_execute(conn, "DELETE FROM books", [])
    {:reply, :ok, state}
  end

  defp ensure_schema(conn) do
    Sqlite3.execute(conn, """
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
    """)
  end

  defp do_query(conn, sql, params) do
    {:ok, stmt} = Sqlite3.prepare(conn, sql)
    :ok = Sqlite3.bind(stmt, params)
    columns = case Sqlite3.columns(conn, stmt) do
      {:ok, cols} -> cols
      _ -> []
    end
    rows = collect_rows(conn, stmt, [])
    :ok = Sqlite3.release(conn, stmt)
    {:ok, columns, rows}
  end

  defp collect_rows(conn, stmt, acc) do
    case Sqlite3.step(conn, stmt) do
      {:row, row} -> collect_rows(conn, stmt, [row | acc])
      :done -> Enum.reverse(acc)
    end
  end

  defp do_execute(conn, sql, params) do
    {:ok, stmt} = Sqlite3.prepare(conn, sql)
    :ok = Sqlite3.bind(stmt, params)
    result = case Sqlite3.step(conn, stmt) do
      :done -> :ok
      {:row, _} -> :ok
      other -> other
    end
    :ok = Sqlite3.release(conn, stmt)
    result
  end

  defp do_last_insert_rowid(conn) do
    {:ok, stmt} = Sqlite3.prepare(conn, "SELECT last_insert_rowid()")
    {:row, [id]} = Sqlite3.step(conn, stmt)
    :done = Sqlite3.step(conn, stmt)
    :ok = Sqlite3.release(conn, stmt)
    id
  end
end
