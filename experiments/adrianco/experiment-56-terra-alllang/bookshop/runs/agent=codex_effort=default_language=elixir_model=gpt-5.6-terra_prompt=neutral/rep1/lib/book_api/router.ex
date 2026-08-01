defmodule BookApi.Router do
  @moduledoc false

  def route("GET", "/health", _query, _body), do: {200, %{status: "ok"}}
  def route("GET", "/books", query, _body), do: {200, BookApi.Store.list(Map.get(query, "author"))}
  def route("GET", "/books/" <> id, _query, _body), do: fetch(id)
  def route("POST", "/books", _query, body), do: with_book(body, &{201, BookApi.Store.create(&1)})
  def route("PUT", "/books/" <> id, _query, body), do: with_book(body, fn book -> update(id, book) end)
  def route("DELETE", "/books/" <> id, _query, _body), do: delete(id)
  def route(_, _, _, _), do: {404, %{error: "not found"}}

  defp fetch(id) do
    case valid_id(id) do
      {:ok, book_id} -> case BookApi.Store.get(book_id) do nil -> not_found(); book -> {200, book} end
      :error -> not_found()
    end
  end
  defp update(id, book) do
    case valid_id(id) do
      {:ok, book_id} -> case BookApi.Store.update(book_id, book) do nil -> not_found(); updated -> {200, updated} end
      :error -> not_found()
    end
  end
  defp delete(id) do
    case valid_id(id) do
      {:ok, book_id} -> case BookApi.Store.delete(book_id) do nil -> not_found(); _ -> {204, nil} end
      :error -> not_found()
    end
  end
  defp not_found, do: {404, %{error: "book not found"}}

  defp with_book(body, action) do
    with {:ok, params} <- BookApi.JSON.decode(body),
         {:ok, book} <- validate(params) do
      action.(book)
    else
      {:error, reason} -> {422, %{error: reason}}
    end
  end
  defp validate(params) when is_map(params) do
    title = Map.get(params, "title")
    author = Map.get(params, "author")
    year = Map.get(params, "year")
    isbn = Map.get(params, "isbn")
    cond do
      not (is_binary(title) and String.trim(title) != "") -> {:error, "title is required"}
      not (is_binary(author) and String.trim(author) != "") -> {:error, "author is required"}
      not (is_nil(year) or is_integer(year)) -> {:error, "year must be an integer"}
      not (is_nil(isbn) or is_binary(isbn) or is_integer(isbn)) -> {:error, "isbn must be a string"}
      true -> {:ok, %{title: String.trim(title), author: String.trim(author), year: year, isbn: if(is_nil(isbn), do: nil, else: to_string(isbn))}}
    end
  end
  defp validate(_), do: {:error, "request body must be a JSON object"}
  defp valid_id(id) do
    case Integer.parse(id) do {value, ""} when value > 0 -> {:ok, value}; _ -> :error end
  end
end
