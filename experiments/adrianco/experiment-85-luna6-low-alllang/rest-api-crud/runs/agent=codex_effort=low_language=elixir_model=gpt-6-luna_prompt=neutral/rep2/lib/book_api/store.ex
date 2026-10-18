defmodule BookApi.Store do
  use GenServer

  def start_link(path), do: GenServer.start_link(__MODULE__, path, name: __MODULE__)

  def init(path) do
    File.mkdir_p!(Path.dirname(path))
    GenServer.cast(self(), :schema)
    {:ok, %{path: path}}
  end

  def handle_cast(:schema, state) do
    sql(
      state,
      "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT);"
    )

    {:noreply, state}
  end

  def create(book), do: GenServer.call(__MODULE__, {:create, book})
  def list(author \\ nil), do: GenServer.call(__MODULE__, {:list, author})
  def get(id), do: GenServer.call(__MODULE__, {:get, id})
  def update(id, book), do: GenServer.call(__MODULE__, {:update, id, book})
  def delete(id), do: GenServer.call(__MODULE__, {:delete, id})

  def handle_call({:create, book}, _from, state) do
    result =
      query(
        state,
        "INSERT INTO books (title,author,year,isbn) VALUES (#{q(book["title"])},#{q(book["author"])},#{nullable(book["year"])},#{nullable(book["isbn"])}); SELECT * FROM books WHERE id=last_insert_rowid();"
      )
      |> List.first()

    {:reply, result, state}
  end

  def handle_call({:list, author}, _from, state) do
    where = if is_binary(author), do: " WHERE author = #{q(author)}", else: ""
    {:reply, query(state, "SELECT * FROM books#{where} ORDER BY id;"), state}
  end

  def handle_call({:get, id}, _from, state),
    do: {:reply, query(state, "SELECT * FROM books WHERE id=#{id};") |> List.first(), state}

  def handle_call({:update, id, book}, _from, state) do
    sql(
      state,
      "UPDATE books SET title=#{q(book["title"])}, author=#{q(book["author"])}, year=#{nullable(book["year"])}, isbn=#{nullable(book["isbn"])} WHERE id=#{id};"
    )

    {:reply, query(state, "SELECT * FROM books WHERE id=#{id};") |> List.first(), state}
  end

  def handle_call({:delete, id}, _from, state) do
    exists = query(state, "SELECT * FROM books WHERE id=#{id};") |> List.first()
    sql(state, "DELETE FROM books WHERE id=#{id};")
    {:reply, exists != nil, state}
  end

  defp sql(state, statement),
    do: System.cmd("sqlite3", [state.path, statement], stderr_to_stdout: true)

  defp query(state, statement) do
    {out, 0} = System.cmd("sqlite3", ["-json", state.path, statement], stderr_to_stdout: true)

    case BookApi.JSON.decode(String.trim(out)) do
      {:ok, rows} when is_list(rows) -> Enum.map(rows, &normalize/1)
      _ -> []
    end
  end

  defp normalize(row) do
    row
    |> Map.update("year", nil, fn year -> year end)
  end

  defp q(nil), do: "NULL"
  defp q(value) when is_binary(value), do: "'" <> String.replace(value, "'", "''") <> "'"
  defp q(value), do: to_string(value)
  defp nullable(nil), do: "NULL"
  defp nullable(""), do: "NULL"
  defp nullable(value), do: q(value)
end
