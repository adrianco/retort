defmodule BookApi.Store do
  @moduledoc false

  def setup(path \\ database_path()) do
    File.mkdir_p!(Path.dirname(path))
    execute!("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT);")
    :ok
  end

  def list(author \\ nil) do
    sql = if author, do: "SELECT id, title, author, year, isbn FROM books WHERE author = #{sql_quote(author)} ORDER BY id", else: "SELECT id, title, author, year, isbn FROM books ORDER BY id"
    query!(sql)
  end

  def get(id), do: query!("SELECT id, title, author, year, isbn FROM books WHERE id = #{integer(id)}") |> List.first()

  def create(book) do
    query!("INSERT INTO books (title, author, year, isbn) VALUES (#{sql_quote(book.title)}, #{sql_quote(book.author)}, #{nullable_integer(book.year)}, #{nullable_quote(book.isbn)}) RETURNING id, title, author, year, isbn") |> List.first()
  end

  def update(id, book) do
    execute!("UPDATE books SET title = #{sql_quote(book.title)}, author = #{sql_quote(book.author)}, year = #{nullable_integer(book.year)}, isbn = #{nullable_quote(book.isbn)} WHERE id = #{integer(id)};")
    get(id)
  end

  def delete(id) do
    case get(id) do
      nil -> nil
      book -> execute!("DELETE FROM books WHERE id = #{integer(id)};"); book
    end
  end

  defp database_path, do: Application.get_env(:book_api, :database_path, "books.db")
  defp query!(sql) do
    {output, 0} = System.cmd("sqlite3", [database_path(), "-json", sql], stderr_to_stdout: true)
    if String.trim(output) == "" do
      []
    else
      {:ok, rows} = BookApi.JSON.decode(output)
      rows
    end
  end
  defp execute!(sql) do
    {_output, 0} = System.cmd("sqlite3", [database_path(), sql], stderr_to_stdout: true)
    :ok
  end
  defp sql_quote(value), do: "'" <> String.replace(to_string(value), "'", "''") <> "'"
  defp nullable_quote(nil), do: "NULL"
  defp nullable_quote(value), do: sql_quote(value)
  defp nullable_integer(nil), do: "NULL"
  defp nullable_integer(value), do: integer(value)
  defp integer(value) when is_integer(value), do: Integer.to_string(value)
  defp integer(value) when is_binary(value) do
    case Integer.parse(value) do
      {integer, ""} -> Integer.to_string(integer)
      _ -> raise ArgumentError, "invalid id or year"
    end
  end
end
