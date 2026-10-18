defmodule BookApi.Store do
  use GenServer

  @table """
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )
  """

  def start_link(database), do: GenServer.start_link(__MODULE__, database, name: __MODULE__)

  def list(author \\ nil), do: GenServer.call(__MODULE__, {:list, author})
  def get(id), do: GenServer.call(__MODULE__, {:get, id})
  def create(attrs), do: GenServer.call(__MODULE__, {:create, attrs})
  def update(id, attrs), do: GenServer.call(__MODULE__, {:update, id, attrs})
  def delete(id), do: GenServer.call(__MODULE__, {:delete, id})

  @impl true
  def init(database) do
    path = if database == ":memory:", do: database, else: Path.expand(database)
    unless path == ":memory:", do: File.mkdir_p!(Path.dirname(path))
    {:ok, conn} = Exqlite.Sqlite3.open(path)
    {:ok, _} = Exqlite.Sqlite3.execute(conn, @table)
    {:ok, conn}
  end

  @impl true
  def handle_call({:list, author}, _from, conn) do
    sql =
      if author in [nil, ""],
        do: "SELECT id,title,author,year,isbn FROM books ORDER BY id",
        else: "SELECT id,title,author,year,isbn FROM books WHERE author = ? ORDER BY id"

    result = query(conn, sql, if(author in [nil, ""], do: [], else: [author]))
    {:reply, result, conn}
  end

  def handle_call({:get, id}, _from, conn) do
    case query(conn, "SELECT id,title,author,year,isbn FROM books WHERE id = ?", [id]) do
      {:ok, [book]} -> {:reply, {:ok, book}, conn}
      {:ok, []} -> {:reply, :not_found, conn}
      error -> {:reply, error, conn}
    end
  end

  def handle_call({:create, attrs}, _from, conn) do
    case execute(conn, "INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)", values(attrs)) do
      :ok ->
        {:ok, [book]} =
          query(
            conn,
            "SELECT id,title,author,year,isbn FROM books WHERE id = last_insert_rowid()",
            []
          )

        {:reply, {:ok, book}, conn}

      error ->
        {:reply, error, conn}
    end
  end

  def handle_call({:update, id, attrs}, _from, conn) do
    case execute(
           conn,
           "UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?",
           values(attrs) ++ [id]
         ) do
      :ok ->
        case query(conn, "SELECT id,title,author,year,isbn FROM books WHERE id=?", [id]) do
          {:ok, [book]} -> {:reply, {:ok, book}, conn}
          {:ok, []} -> {:reply, :not_found, conn}
          error -> {:reply, error, conn}
        end

      error ->
        {:reply, error, conn}
    end
  end

  def handle_call({:delete, id}, _from, conn) do
    case query(conn, "SELECT id,title,author,year,isbn FROM books WHERE id=?", [id]) do
      {:ok, [book]} ->
        :ok = execute(conn, "DELETE FROM books WHERE id=?", [id])
        {:reply, {:ok, book}, conn}

      {:ok, []} ->
        {:reply, :not_found, conn}

      error ->
        {:reply, error, conn}
    end
  end

  defp values(attrs), do: [attrs["title"], attrs["author"], attrs["year"], attrs["isbn"]]

  defp execute(conn, sql, params) do
    with {:ok, statement} <- Exqlite.Sqlite3.prepare(conn, sql),
         :ok <- Exqlite.Sqlite3.bind(conn, statement, params),
         :done <- Exqlite.Sqlite3.step(conn, statement) do
      Exqlite.Sqlite3.release(conn, statement)
    end
  end

  defp query(conn, sql, params) do
    with {:ok, statement} <- Exqlite.Sqlite3.prepare(conn, sql),
         :ok <- Exqlite.Sqlite3.bind(conn, statement, params),
         {:ok, rows} <- collect(conn, statement, []) do
      :ok = Exqlite.Sqlite3.release(conn, statement)

      {:ok,
       Enum.map(rows, fn [id, title, author, year, isbn] ->
         %{"id" => id, "title" => title, "author" => author, "year" => year, "isbn" => isbn}
       end)}
    end
  end

  defp collect(conn, statement, rows) do
    case Exqlite.Sqlite3.step(conn, statement) do
      :done -> {:ok, Enum.reverse(rows)}
      {:row, row} -> collect(conn, statement, [row | rows])
      error -> error
    end
  end
end
