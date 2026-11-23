defmodule BookCollection.Store do
  use GenServer

  require Logger
  alias Exqlite.Sqlite3

  @columns "id, title, author, year, isbn"

  def start_link(path), do: GenServer.start_link(__MODULE__, path, name: __MODULE__)

  def health, do: query("SELECT 1", [])
  def list(nil), do: books("SELECT #{@columns} FROM books ORDER BY id", [])

  def list(author),
    do: books("SELECT #{@columns} FROM books WHERE author = ? ORDER BY id", [author])

  def get(id), do: book("SELECT #{@columns} FROM books WHERE id = ?", [id])

  def create(fields),
    do:
      book(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING #{@columns}",
        fields
      )

  def update(id, fields),
    do:
      book(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING #{@columns}",
        fields ++ [id]
      )

  def delete(id), do: book("DELETE FROM books WHERE id = ? RETURNING #{@columns}", [id])

  @impl true
  def init(path) do
    with {:ok, db} <- Sqlite3.open(path) do
      case Sqlite3.execute(db, """
           CREATE TABLE IF NOT EXISTS books (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             title TEXT NOT NULL,
             author TEXT NOT NULL,
             year INTEGER,
             isbn TEXT
           )
           """) do
        :ok ->
          {:ok, db}

        {:error, reason} ->
          Sqlite3.close(db)
          {:stop, reason}
      end
    else
      {:error, reason} -> {:stop, reason}
    end
  end

  @impl true
  def handle_call({sql, params}, _from, db) do
    result =
      with {:ok, statement} <- Sqlite3.prepare(db, sql) do
        try do
          with :ok <- Sqlite3.bind(statement, params), do: Sqlite3.fetch_all(db, statement)
        after
          Sqlite3.release(db, statement)
        end
      end

    if match?({:error, _}, result), do: Logger.error("SQLite request failed: #{inspect(result)}")
    {:reply, result, db}
  end

  defp query(sql, params), do: GenServer.call(__MODULE__, {sql, params})

  defp books(sql, params) do
    with {:ok, rows} <- query(sql, params), do: {:ok, Enum.map(rows, &to_book/1)}
  end

  defp book(sql, params) do
    case query(sql, params) do
      {:ok, [row]} -> {:ok, to_book(row)}
      {:ok, []} -> {:error, :not_found}
      {:error, reason} -> {:error, reason}
    end
  end

  defp to_book([id, title, author, year, isbn]),
    do: %{id: id, title: title, author: author, year: year, isbn: isbn}
end
