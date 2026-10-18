defmodule BooksApi.Book do
  @moduledoc """
  Book persistence and validation. Errors are returned as `{:error, errors}`
  where `errors` is a map of field => message.
  """

  alias BooksApi.Repo

  @columns "id, title, author, year, isbn"

  def list(author \\ nil) do
    result =
      if author,
        do: Repo.query("SELECT #{@columns} FROM books WHERE author = ? ORDER BY id", [author]),
        else: Repo.query("SELECT #{@columns} FROM books ORDER BY id")

    map_rows(result)
  end

  def get(id) do
    case Repo.query("SELECT #{@columns} FROM books WHERE id = ?", [id]) do
      {:ok, [row]} -> {:ok, to_map(row)}
      {:ok, []} -> {:error, :not_found}
      {:error, _} = err -> err
    end
  end

  def create(attrs) do
    with {:ok, data} <- validate(attrs),
         {:ok, _} <-
           Repo.query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", [
             data.title,
             data.author,
             data.year,
             data.isbn
           ]),
         {:ok, [[id]]} <- Repo.query("SELECT last_insert_rowid()") do
      get(id)
    else
      {:error, errors} when is_map(errors) -> {:error, errors}
      other -> other
    end
  end

  def update(id, attrs) do
    with {:ok, _existing} <- get(id),
         {:ok, data} <- validate(attrs),
         {:ok, _} <-
           Repo.query(
             "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
             [data.title, data.author, data.year, data.isbn, id]
           ) do
      get(id)
    else
      {:error, errors} when is_map(errors) -> {:error, errors}
      other -> other
    end
  end

  def delete(id) do
    with {:ok, _existing} <- get(id),
         {:ok, _} <- Repo.query("DELETE FROM books WHERE id = ?", [id]) do
      :ok
    end
  end

  @doc "Validates and normalizes attributes. `title` and `author` are required non-empty strings."
  def validate(attrs) when is_map(attrs) do
    attrs = Map.new(attrs, fn {k, v} -> {to_string(k), v} end)

    errors =
      %{}
      |> require_string(attrs, "title")
      |> require_string(attrs, "author")
      |> optional(attrs, "year", &valid_year/1)
      |> optional(attrs, "isbn", &valid_string/1)

    if map_size(errors) == 0 do
      {:ok,
       %{
         title: String.trim(attrs["title"]),
         author: String.trim(attrs["author"]),
         year: attrs["year"],
         isbn: attrs["isbn"]
       }}
    else
      {:error, errors}
    end
  end

  def validate(_), do: {:error, %{"body" => "must be a JSON object"}}

  defp require_string(errors, attrs, key) do
    case attrs[key] do
      v when is_binary(v) ->
        if String.trim(v) == "", do: Map.put(errors, key, "must not be blank"), else: errors

      nil ->
        Map.put(errors, key, "is required")

      _ ->
        Map.put(errors, key, "must be a string")
    end
  end

  defp optional(errors, attrs, key, check) do
    case Map.fetch(attrs, key) do
      :error -> errors
      {:ok, nil} -> errors
      {:ok, v} -> if check.(v), do: errors, else: Map.put(errors, key, "is invalid")
    end
  end

  defp valid_year(v), do: is_integer(v) and v >= 0 and v <= 9999
  defp valid_string(v), do: is_binary(v)

  defp map_rows({:ok, rows}), do: {:ok, Enum.map(rows, &to_map/1)}
  defp map_rows(other), do: other

  defp to_map([id, title, author, year, isbn]) do
    %{id: id, title: title, author: author, year: year, isbn: isbn}
  end
end
