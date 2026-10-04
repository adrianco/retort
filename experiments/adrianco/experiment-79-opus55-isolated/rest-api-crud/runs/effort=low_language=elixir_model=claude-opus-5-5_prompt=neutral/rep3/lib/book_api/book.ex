defmodule BookApi.Book do
  @moduledoc "Validation of incoming book payloads."

  # Largest value SQLite can store in an INTEGER column.
  @max_int 9_223_372_036_854_775_807

  @doc """
  Validates a decoded JSON payload. Returns `{:ok, attrs}` with atom keys or
  `{:error, errors}` where `errors` maps field names to messages.
  """
  def validate(params) when is_map(params) do
    fields = [
      title: required_string(params["title"]),
      author: required_string(params["author"]),
      year: optional_integer(params["year"]),
      isbn: optional_string(params["isbn"])
    ]

    case for {field, {:error, msg}} <- fields, into: %{}, do: {field, msg} do
      errors when errors == %{} -> {:ok, Map.new(fields, fn {k, {:ok, v}} -> {k, v} end)}
      errors -> {:error, errors}
    end
  end

  def validate(_), do: {:error, %{body: "must be a JSON object"}}

  defp required_string(nil), do: {:error, "is required"}

  defp required_string(value) when is_binary(value) do
    case String.trim(value) do
      "" -> {:error, "is required"}
      trimmed -> {:ok, trimmed}
    end
  end

  defp required_string(_), do: {:error, "must be a string"}

  defp optional_string(nil), do: {:ok, nil}
  defp optional_string(value) when is_binary(value), do: {:ok, value}
  defp optional_string(_), do: {:error, "must be a string"}

  defp optional_integer(nil), do: {:ok, nil}

  defp optional_integer(value) when is_integer(value) and abs(value) <= @max_int,
    do: {:ok, value}

  defp optional_integer(_), do: {:error, "must be an integer"}
end
