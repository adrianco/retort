defmodule BooksApi.Repo do
  @moduledoc """
  Owns a single SQLite connection and serializes all access through it.
  """
  use GenServer

  alias Exqlite.Sqlite3

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: Keyword.get(opts, :name, __MODULE__))
  end

  @doc "Runs a statement with positional params. Returns `{:ok, rows}` (rows are lists of column values)."
  def query(sql, params \\ [], server \\ __MODULE__) do
    GenServer.call(server, {:query, sql, params})
  end

  @impl true
  def init(opts) do
    path = Keyword.get(opts, :path, Application.get_env(:books_api, :database_path))
    {:ok, conn} = Sqlite3.open(path)
    :ok = create_schema(conn)
    {:ok, %{conn: conn}}
  end

  @impl true
  def handle_call({:query, sql, params}, _from, %{conn: conn} = state) do
    {:reply, run(conn, sql, params), state}
  end

  defp run(conn, sql, params) do
    with {:ok, stmt} <- Sqlite3.prepare(conn, sql),
         :ok <- Sqlite3.bind(stmt, params),
         result = Sqlite3.fetch_all(conn, stmt),
         :ok <- Sqlite3.release(conn, stmt) do
      result
    end
  end

  defp create_schema(conn) do
    {:ok, stmt} =
      Sqlite3.prepare(conn, """
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
      """)

    :done = Sqlite3.step(conn, stmt)
    :ok = Sqlite3.release(conn, stmt)
  end
end
