defmodule BookApi.Books do
  @moduledoc """
  Book collection operations: validation plus persistence.

  Functions return `{:ok, book}`, `{:ok, [book]}`, `:ok`, `{:error, :not_found}`,
  `{:error, {:validation, errors}}` or `{:error, reason}` for database failures.
  """
  alias BookApi.DB

  @select "SELECT id, title, author, year, isbn FROM books"

  @spec create(map()) :: {:ok, map()} | {:error, term()}
  def create(attrs) do
    with {:ok, data} <- validate(attrs),
         {:ok, %{last_insert_id: id}} <-
           DB.query("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", params(data)) do
      get(id)
    end
  end

  @spec list(map()) :: {:ok, [map()]} | {:error, term()}
  def list(filters \\ %{}) do
    {where, args} =
      case Map.get(filters, "author") do
        nil -> {"", []}
        author -> {" WHERE author = ? COLLATE NOCASE", [author]}
      end

    with {:ok, %{rows: rows}} <- DB.query(@select <> where <> " ORDER BY id", args) do
      {:ok, Enum.map(rows, &to_book/1)}
    end
  end

  @spec get(integer()) :: {:ok, map()} | {:error, term()}
  def get(id) do
    case DB.query(@select <> " WHERE id = ?", [id]) do
      {:ok, %{rows: [row]}} -> {:ok, to_book(row)}
      {:ok, %{rows: []}} -> {:error, :not_found}
      {:error, reason} -> {:error, reason}
    end
  end

  @spec update(integer(), map()) :: {:ok, map()} | {:error, term()}
  def update(id, attrs) do
    with {:ok, data} <- validate(attrs),
         {:ok, _book} <- get(id),
         {:ok, _} <-
           DB.query(
             "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
             params(data) ++ [id]
           ) do
      get(id)
    end
  end

  @spec delete(integer()) :: :ok | {:error, term()}
  def delete(id) do
    with {:ok, _book} <- get(id),
         {:ok, _} <- DB.query("DELETE FROM books WHERE id = ?", [id]) do
      :ok
    end
  end

  @doc "Validates a book payload. Returns normalized data or a map of field errors."
  def validate(attrs) when is_map(attrs) do
    case field_errors(attrs) do
      errors when map_size(errors) == 0 ->
        {:ok,
         %{
           title: String.trim(attrs["title"]),
           author: String.trim(attrs["author"]),
           year: attrs["year"],
           isbn: attrs["isbn"]
         }}

      errors ->
        {:error, {:validation, errors}}
    end
  end

  def validate(_attrs), do: {:error, {:validation, %{"body" => "must be a JSON object"}}}

  defp field_errors(attrs) do
    [
      required_string(attrs, "title"),
      required_string(attrs, "author"),
      year_error(attrs["year"]),
      isbn_error(attrs["isbn"])
    ]
    |> Enum.reject(&is_nil/1)
    |> Map.new()
  end

  defp required_string(attrs, key) do
    case attrs[key] do
      nil -> {key, "is required"}
      value when is_binary(value) -> if String.trim(value) == "", do: {key, "must not be blank"}
      _ -> {key, "must be a string"}
    end
  end

  defp year_error(nil), do: nil
  defp year_error(year) when is_integer(year) and year >= 0 and year <= 9999, do: nil
  defp year_error(_), do: {"year", "must be an integer between 0 and 9999"}

  defp isbn_error(nil), do: nil
  defp isbn_error(isbn) when is_binary(isbn), do: nil
  defp isbn_error(_), do: {"isbn", "must be a string"}

  defp params(data), do: [data.title, data.author, data.year, data.isbn]

  defp to_book([id, title, author, year, isbn]) do
    %{id: id, title: title, author: author, year: year, isbn: isbn}
  end
end
