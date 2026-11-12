defmodule BookApi.Store do
  @moduledoc """
  SQLite-backed book storage. A single GenServer owns the connection and
  serializes access to it.
  """
  use GenServer

  alias Exqlite.Sqlite3

  @columns "id, title, author, year, isbn"

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: Keyword.get(opts, :name, __MODULE__))
  end

  def list(filters \\ %{}, server \\ __MODULE__), do: GenServer.call(server, {:list, filters})
  def get(id, server \\ __MODULE__), do: GenServer.call(server, {:get, id})
  def create(attrs, server \\ __MODULE__), do: GenServer.call(server, {:create, attrs})
  def update(id, attrs, server \\ __MODULE__), do: GenServer.call(server, {:update, id, attrs})
  def delete(id, server \\ __MODULE__), do: GenServer.call(server, {:delete, id})
  def delete_all(server \\ __MODULE__), do: GenServer.call(server, :delete_all)

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
  def handle_call({:list, filters}, _from, conn) do
    rows =
      case filters do
        %{author: author} when is_binary(author) ->
          query(conn, "SELECT #{@columns} FROM books WHERE author = ?1 ORDER BY id", [author])

        _ ->
          query(conn, "SELECT #{@columns} FROM books ORDER BY id", [])
      end

    {:reply, Enum.map(rows, &to_book/1), conn}
  end

  def handle_call({:get, id}, _from, conn), do: {:reply, fetch(conn, id), conn}

  def handle_call({:create, a}, _from, conn) do
    query(conn, "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)", [
      a.title,
      a.author,
      a.year,
      a.isbn
    ])

    {:ok, id} = Sqlite3.last_insert_rowid(conn)
    {:reply, fetch(conn, id), conn}
  end

  def handle_call({:update, id, a}, _from, conn) do
    query(conn, "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5", [
      a.title,
      a.author,
      a.year,
      a.isbn,
      id
    ])

    {:reply, fetch(conn, id), conn}
  end

  def handle_call({:delete, id}, _from, conn) do
    query(conn, "DELETE FROM books WHERE id = ?1", [id])
    {:ok, changes} = Sqlite3.changes(conn)
    {:reply, if(changes > 0, do: :ok, else: {:error, :not_found}), conn}
  end

  def handle_call(:delete_all, _from, conn) do
    query(conn, "DELETE FROM books", [])
    {:reply, :ok, conn}
  end

  @impl true
  def terminate(_reason, conn), do: Sqlite3.close(conn)

  defp fetch(conn, id) do
    case query(conn, "SELECT #{@columns} FROM books WHERE id = ?1", [id]) do
      [row] -> {:ok, to_book(row)}
      [] -> {:error, :not_found}
    end
  end

  defp query(conn, sql, params) do
    {:ok, stmt} = Sqlite3.prepare(conn, sql)

    try do
      :ok = Sqlite3.bind(stmt, params)
      {:ok, rows} = Sqlite3.fetch_all(conn, stmt)
      rows
    after
      Sqlite3.release(conn, stmt)
    end
  end

  defp to_book([id, title, author, year, isbn]) do
    %{id: id, title: title, author: author, year: year, isbn: isbn}
  end
end
