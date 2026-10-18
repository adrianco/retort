defmodule BookApi.Router do
  def dispatch("GET", "/health", _body, _query), do: response(200, %{status: "ok"})

  def dispatch("POST", "/books", body, _query) do
    with {:ok, book} <- BookApi.JSON.decode(body), :ok <- validate(book) do
      response(201, BookApi.Store.create(book))
    else
      {:error, :invalid_json} -> response(400, %{error: "Invalid JSON body"})
      {:error, message} -> response(422, %{error: message})
    end
  end

  def dispatch("GET", "/books", _body, query),
    do: response(200, BookApi.Store.list(query["author"]))

  def dispatch("GET", "/books/" <> raw_id, _body, _query) do
    with {:ok, id} <- parse_id(raw_id), book when not is_nil(book) <- BookApi.Store.get(id) do
      response(200, book)
    else
      _ -> response(404, %{error: "Book not found"})
    end
  end

  def dispatch("PUT", "/books/" <> raw_id, body, _query) do
    with {:ok, id} <- parse_id(raw_id),
         {:ok, book} <- BookApi.JSON.decode(body),
         :ok <- validate(book),
         updated when not is_nil(updated) <- BookApi.Store.update(id, book) do
      response(200, updated)
    else
      {:error, :invalid_json} -> response(400, %{error: "Invalid JSON body"})
      {:error, message} -> response(422, %{error: message})
      _ -> response(404, %{error: "Book not found"})
    end
  end

  def dispatch("DELETE", "/books/" <> raw_id, _body, _query) do
    case parse_id(raw_id) do
      {:ok, id} ->
        if BookApi.Store.delete(id),
          do: {204, ""},
          else: response(404, %{error: "Book not found"})

      _ ->
        response(404, %{error: "Book not found"})
    end
  end

  def dispatch(_, _, _, _), do: response(404, %{error: "Not found"})

  defp validate(book) when is_map(book) do
    if nonempty?(book["title"]) and nonempty?(book["author"]),
      do: :ok,
      else: {:error, "title and author are required"}
  end

  defp validate(_), do: {:error, "Expected a JSON object"}
  defp nonempty?(value), do: is_binary(value) and String.trim(value) != ""

  defp parse_id(id) do
    case Integer.parse(id) do
      {n, ""} when n > 0 -> {:ok, n}
      _ -> :error
    end
  end

  defp response(status, body), do: {status, BookApi.JSON.encode(body)}
end
