defmodule BookApi.Book do
  @moduledoc """
  Validation of book attributes coming from request bodies.
  """

  @doc """
  Validates a decoded JSON body.

  Returns `{:ok, attrs}` with `:title`, `:author`, `:year` and `:isbn` keys, or
  `{:error, errors}` where `errors` maps field names to messages.
  """
  def validate(params) when is_map(params) do
    {attrs, errors} =
      Enum.reduce(
        [
          {:title, &required_string/1},
          {:author, &required_string/1},
          {:year, &optional_integer/1},
          {:isbn, &optional_string/1}
        ],
        {%{}, %{}},
        fn {field, check}, {attrs, errors} ->
          case check.(Map.get(params, Atom.to_string(field))) do
            {:ok, value} -> {Map.put(attrs, field, value), errors}
            {:error, message} -> {attrs, Map.put(errors, field, message)}
          end
        end
      )

    if errors == %{}, do: {:ok, attrs}, else: {:error, errors}
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

  defp optional_integer(nil), do: {:ok, nil}
  defp optional_integer(value) when is_integer(value), do: {:ok, value}
  defp optional_integer(_), do: {:error, "must be an integer"}

  defp optional_string(nil), do: {:ok, nil}
  defp optional_string(value) when is_binary(value), do: {:ok, value}
  defp optional_string(_), do: {:error, "must be a string"}
end
