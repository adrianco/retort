defmodule BookApi.Book do
  @moduledoc "Validation of incoming book payloads."

  @doc """
  Validates decoded JSON params. Returns `{:ok, attrs}` or `{:error, errors}`
  where `errors` maps field names to messages.
  """
  def validate(params) when is_map(params) do
    fields = [
      {:title, required_string(params["title"])},
      {:author, required_string(params["author"])},
      {:year, optional_integer(params["year"])},
      {:isbn, optional_string(params["isbn"])}
    ]

    case for {field, {:error, msg}} <- fields, into: %{}, do: {field, msg} do
      errors when errors == %{} -> {:ok, Map.new(fields, fn {field, {:ok, v}} -> {field, v} end)}
      errors -> {:error, errors}
    end
  end

  defp required_string(nil), do: {:error, "is required"}

  defp required_string(value) when is_binary(value) do
    case String.trim(value) do
      "" -> {:error, "is required"}
      trimmed -> {:ok, trimmed}
    end
  end

  defp required_string(_), do: {:error, "must be a string"}

  defp optional_integer(nil), do: {:ok, nil}
  defp optional_integer(value) when is_integer(value), do: {:ok, value}
  defp optional_integer(_), do: {:error, "must be an integer"}

  defp optional_string(nil), do: {:ok, nil}
  defp optional_string(value) when is_binary(value), do: {:ok, value}
  defp optional_string(_), do: {:error, "must be a string"}
end
