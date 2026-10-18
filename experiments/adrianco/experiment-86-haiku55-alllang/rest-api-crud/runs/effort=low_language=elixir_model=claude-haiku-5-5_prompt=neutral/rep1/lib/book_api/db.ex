defmodule BookApi.DB do
  @moduledoc """
  Owns the single SQLite connection. All queries are serialized through this
  GenServer, which keeps the embedded database safe under concurrent requests.
  """
  use GenServer

  alias Exqlite.Sqlite3

  @schema """
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )
  """

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: Keyword.get(opts, :name, __MODULE__))
  end

  @doc """
  Runs a SQL statement with positional params. Returns
  `{:ok, %{rows: rows, last_insert_id: id, changes: n}}` or `{:error, reason}`.
  """
  def query(sql, params \\ [], server \\ __MODULE__) do
    GenServer.call(server, {:query, sql, params})
  end

  @impl true
  def init(opts) do
    path = Keyword.fetch!(opts, :path)
    File.mkdir_p!(Path.dirname(path))

    {:ok, conn} = Sqlite3.open(path)
    :ok = Sqlite3.execute(conn, @schema)
    {:ok, conn}
  end

  @impl true
  def handle_call({:query, sql, params}, _from, conn) do
    {:reply, run(conn, sql, params), conn}
  end

  defp run(conn, sql, params) do
    case Sqlite3.prepare(conn, sql) do
      {:ok, stmt} ->
        try do
          with :ok <- Sqlite3.bind(stmt, params),
               {:ok, rows} <- collect(conn, stmt, []) do
            {:ok,
             %{
               rows: rows,
               last_insert_id: unwrap(Sqlite3.last_insert_rowid(conn)),
               changes: unwrap(Sqlite3.changes(conn))
             }}
          end
        after
          Sqlite3.release(conn, stmt)
        end

      {:error, reason} ->
        {:error, reason}
    end
  end

  defp unwrap({:ok, value}), do: value
  defp unwrap(value), do: value

  defp collect(conn, stmt, acc) do
    case Sqlite3.step(conn, stmt) do
      {:row, row} -> collect(conn, stmt, [row | acc])
      :done -> {:ok, Enum.reverse(acc)}
      {:error, reason} -> {:error, reason}
    end
  end
end
