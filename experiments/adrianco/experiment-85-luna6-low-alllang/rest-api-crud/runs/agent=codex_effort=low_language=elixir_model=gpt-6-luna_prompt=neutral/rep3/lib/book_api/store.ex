defmodule BookApi.Store do
  defp db, do: System.get_env("BOOKS_DB", "books.sqlite3")

  def init do
    sql("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT);")
  end

  def list(author \\ nil) do
    where = if author, do: " WHERE lower(author) = lower(" <> q(author) <> ")", else: ""
    query("SELECT id,title,author,year,isbn FROM books" <> where <> " ORDER BY id;")
  end
  def get(id), do: one("SELECT id,title,author,year,isbn FROM books WHERE id=#{id};")
  def create(book) do
    sql("INSERT INTO books(title,author,year,isbn) VALUES(#{q(book["title"])},#{q(book["author"])},#{val(book["year"])},#{val(book["isbn"])});")
    get(last_id())
  end
  def update(id, book) do
    sql("UPDATE books SET title=#{q(book["title"])},author=#{q(book["author"])},year=#{val(book["year"])},isbn=#{val(book["isbn"])} WHERE id=#{id};")
    get(id)
  end
  def delete(id) do
    existed = get(id)
    sql("DELETE FROM books WHERE id=#{id};")
    existed != nil
  end

  defp one(statement) do
    case query(statement) do [book | _] -> book; _ -> nil end
  end
  defp query(statement) do
    case System.cmd("sqlite3", ["-json", db(), statement], stderr_to_stdout: true) do
      {output, 0} -> case BookApi.JSON.decode(String.trim(output)) do {:ok, result} when is_list(result) -> Enum.map(result, &normalize/1); _ -> [] end
      {error, _} -> raise "SQLite error: #{error}"
    end
  end
  defp sql(statement) do
    case System.cmd("sqlite3", [db(), statement], stderr_to_stdout: true) do {_, 0} -> :ok; {error, _} -> raise "SQLite error: #{error}" end
  end
  defp last_id do
    {value, 0} = System.cmd("sqlite3", [db(), "SELECT last_insert_rowid();"])
    # Each sqlite3 process has its own connection; locate inserted row by max id instead.
    _ = value
    case query("SELECT max(id) AS id FROM books;") do [%{"id" => id}] -> id; _ -> nil end
  end
  defp normalize(map), do: Map.new(map, fn {key, value} -> {key, value} end)
  defp q(nil), do: "NULL"
  defp q(value), do: "'" <> (to_string(value) |> String.replace("'", "''")) <> "'"
  defp val(nil), do: "NULL"
  defp val(value) when is_integer(value), do: Integer.to_string(value)
  defp val(value) when is_float(value), do: Float.to_string(value)
  defp val(value), do: q(value)
end
