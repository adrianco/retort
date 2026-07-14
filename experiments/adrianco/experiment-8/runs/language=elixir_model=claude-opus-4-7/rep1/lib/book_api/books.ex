defmodule BookApi.Books do
  @moduledoc "Book CRUD operations backed by BookApi.Repo."

  alias BookApi.Repo

  @columns ["id", "title", "author", "year", "isbn"]

  def list(filters \\ %{}) do
    case Map.get(filters, "author") do
      nil ->
        {:ok, _cols, rows} =
          Repo.query("SELECT id, title, author, year, isbn FROM books ORDER BY id")

        Enum.map(rows, &row_to_map/1)

      author ->
        {:ok, _cols, rows} =
          Repo.query(
            "SELECT id, title, author, year, isbn FROM books WHERE author = ?1 ORDER BY id",
            [author]
          )

        Enum.map(rows, &row_to_map/1)
    end
  end

  def get(id) when is_integer(id) do
    case Repo.query(
           "SELECT id, title, author, year, isbn FROM books WHERE id = ?1",
           [id]
         ) do
      {:ok, _cols, [row]} -> {:ok, row_to_map(row)}
      {:ok, _cols, []} -> {:error, :not_found}
    end
  end

  def get(id) when is_binary(id) do
    case Integer.parse(id) do
      {int_id, ""} -> get(int_id)
      _ -> {:error, :not_found}
    end
  end

  def create(attrs) do
    with {:ok, valid} <- validate(attrs) do
      :ok =
        Repo.execute(
          "INSERT INTO books (title, author, year, isbn) VALUES (?1, ?2, ?3, ?4)",
          [valid["title"], valid["author"], valid["year"], valid["isbn"]]
        )

      new_id = Repo.last_insert_rowid()
      get(new_id)
    end
  end

  def update(id, attrs) do
    with {:ok, book} <- get(id),
         merged = Map.merge(string_keys(book), attrs),
         {:ok, valid} <- validate(merged) do
      :ok =
        Repo.execute(
          "UPDATE books SET title = ?1, author = ?2, year = ?3, isbn = ?4 WHERE id = ?5",
          [valid["title"], valid["author"], valid["year"], valid["isbn"], book.id]
        )

      get(book.id)
    end
  end

  def delete(id) do
    with {:ok, book} <- get(id) do
      :ok = Repo.execute("DELETE FROM books WHERE id = ?1", [book.id])
      :ok
    end
  end

  defp validate(attrs) do
    title = trim(attrs["title"])
    author = trim(attrs["author"])

    errors =
      []
      |> maybe_error(title in [nil, ""], "title is required")
      |> maybe_error(author in [nil, ""], "author is required")
      |> maybe_error(
        attrs["year"] != nil and not is_integer(attrs["year"]),
        "year must be an integer"
      )
      |> maybe_error(
        attrs["isbn"] != nil and not is_binary(attrs["isbn"]),
        "isbn must be a string"
      )

    if errors == [] do
      {:ok,
       %{
         "title" => title,
         "author" => author,
         "year" => attrs["year"],
         "isbn" => attrs["isbn"]
       }}
    else
      {:error, {:validation, Enum.reverse(errors)}}
    end
  end

  defp maybe_error(errors, true, message), do: [message | errors]
  defp maybe_error(errors, false, _message), do: errors

  defp trim(nil), do: nil
  defp trim(s) when is_binary(s), do: String.trim(s)
  defp trim(other), do: other

  defp row_to_map([id, title, author, year, isbn]) do
    %{id: id, title: title, author: author, year: year, isbn: isbn}
  end

  defp string_keys(map) do
    Enum.into(@columns, %{}, fn col -> {col, Map.get(map, String.to_atom(col))} end)
  end
end
