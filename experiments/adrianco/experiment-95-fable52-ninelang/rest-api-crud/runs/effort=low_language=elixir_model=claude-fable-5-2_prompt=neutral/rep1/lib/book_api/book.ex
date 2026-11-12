defmodule BookApi.Book do
  @moduledoc "Validation of incoming book payloads."

  @doc """
  Validates a decoded JSON payload. Returns `{:ok, attrs}` or
  `{:error, errors}` where `errors` maps field names to messages.
  """
  def validate(params) when is_map(params) do
    errors =
      %{}
      |> required_string(params, "title")
      |> required_string(params, "author")
      |> optional(params, "year", &is_integer/1, "must be an integer")
      |> optional(params, "isbn", &is_binary/1, "must be a string")

    if errors == %{} do
      {:ok,
       %{
         title: String.trim(params["title"]),
         author: String.trim(params["author"]),
         year: params["year"],
         isbn: params["isbn"]
       }}
    else
      {:error, errors}
    end
  end

  def validate(_), do: {:error, %{"body" => "must be a JSON object"}}

  defp required_string(errors, params, key) do
    case params[key] do
      nil ->
        Map.put(errors, key, "is required")

      v when is_binary(v) ->
        if String.trim(v) == "", do: Map.put(errors, key, "is required"), else: errors

      _ ->
        Map.put(errors, key, "must be a string")
    end
  end

  defp optional(errors, params, key, valid?, message) do
    case params[key] do
      nil -> errors
      v -> if valid?.(v), do: errors, else: Map.put(errors, key, message)
    end
  end
end
