defmodule Books.Store do
  use GenServer
  alias Exqlite.Sqlite3, as: SQL

  def start_link(_), do: GenServer.start_link(__MODULE__, nil, name: __MODULE__)
  def list(author), do: GenServer.call(__MODULE__, {:list, author})
  def get(id), do: GenServer.call(__MODULE__, {:get, id})
  def create(attrs), do: GenServer.call(__MODULE__, {:create, attrs})
  def update(id, attrs), do: GenServer.call(__MODULE__, {:update, id, attrs})
  def delete(id), do: GenServer.call(__MODULE__, {:delete, id})

  @impl true
  def init(_) do
    {:ok, db} = SQL.open(Application.fetch_env!(:books, :db_path))

    :ok =
      SQL.execute(
        db,
        "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)"
      )

    {:ok, db}
  end

  @impl true
  def handle_call({:list, author}, _from, db) do
    {sql, args} =
      if author,
        do:
          {"SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
           [author]},
        else: {"SELECT id, title, author, year, isbn FROM books ORDER BY id", []}

    {:reply, query(db, sql, args) |> Enum.map(&book/1), db}
  end

  def handle_call({:get, id}, _from, db), do: {:reply, find(db, id), db}

  def handle_call({:create, attrs}, _from, db) do
    query(db, "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", values(attrs))
    {:ok, id} = SQL.last_insert_rowid(db)
    {:reply, find(db, id), db}
  end

  def handle_call({:update, id, attrs}, _from, db) do
    result =
      if find(db, id) do
        query(
          db,
          "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
          values(attrs) ++ [id]
        )

        find(db, id)
      end

    {:reply, result, db}
  end

  def handle_call({:delete, id}, _from, db) do
    found = find(db, id) != nil
    if found, do: query(db, "DELETE FROM books WHERE id = ?", [id])
    {:reply, found, db}
  end

  defp values(attrs), do: Enum.map(["title", "author", "year", "isbn"], &Map.get(attrs, &1))

  defp find(db, id) do
    case query(db, "SELECT id, title, author, year, isbn FROM books WHERE id = ?", [id]) do
      [row] -> book(row)
      [] -> nil
    end
  end

  defp book([id, title, author, year, isbn]),
    do: %{id: id, title: title, author: author, year: year, isbn: isbn}

  defp query(db, sql, args) do
    {:ok, stmt} = SQL.prepare(db, sql)

    try do
      :ok = SQL.bind(stmt, args)
      rows(db, stmt, [])
    after
      SQL.release(db, stmt)
    end
  end

  defp rows(db, stmt, acc) do
    case SQL.step(db, stmt) do
      {:row, row} -> rows(db, stmt, [row | acc])
      :done -> Enum.reverse(acc)
      {:error, error} -> raise "SQLite error: #{inspect(error)}"
    end
  end
end
