defmodule BookApi.JSON do
  @moduledoc "A small JSON codec for the flat request/response documents used by this API."

  def encode(value), do: IO.iodata_to_binary(encode_value(value))
  def decode(binary) when is_binary(binary) do
    with {:ok, value, rest} <- value(skip(binary)),
         true <- skip(rest) == "" do
      {:ok, value}
    else
      false -> {:error, :trailing_data}
      error -> error
    end
  end

  defp encode_value(map) when is_map(map) do
    contents = map |> Enum.map(fn {k, v} -> [encode_value(to_string(k)), ":", encode_value(v)] end) |> Enum.intersperse(",")
    ["{", contents, "}"]
  end
  defp encode_value(list) when is_list(list), do: ["[", Enum.intersperse(Enum.map(list, &encode_value/1), ","), "]"]
  defp encode_value(value) when is_binary(value) do
    escaped = Enum.reduce([{"\\", "\\\\"}, {"\"", "\\\""}, {"\n", "\\n"}, {"\r", "\\r"}, {"\t", "\\t"}], value, fn {pattern, replacement}, text ->
      String.replace(text, pattern, replacement)
    end)
    ["\"", escaped, "\""]
  end
  defp encode_value(value) when is_integer(value) or is_float(value), do: to_string(value)
  defp encode_value(true), do: "true"
  defp encode_value(false), do: "false"
  defp encode_value(nil), do: "null"

  defp value("{" <> rest), do: object(skip(rest), %{})
  defp value("[" <> rest), do: array(skip(rest), [])
  defp value("\"" <> rest), do: string(rest, "")
  defp value("true" <> rest), do: {:ok, true, rest}
  defp value("false" <> rest), do: {:ok, false, rest}
  defp value("null" <> rest), do: {:ok, nil, rest}
  defp value(rest) do
    case Regex.run(~r/^(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)(.*)$/s, rest) do
      [_, number, remaining] -> {:ok, if(String.contains?(number, [".", "e", "E"]), do: String.to_float(number), else: String.to_integer(number)), remaining}
      _ -> {:error, :invalid_json}
    end
  end

  defp object("}" <> rest, acc), do: {:ok, acc, rest}
  defp object(rest, acc) do
    with {:ok, key, ":" <> after_colon} <- value(rest),
         true <- is_binary(key),
         {:ok, val, after_value} <- value(skip(after_colon)) do
      case skip(after_value) do
        "," <> more -> object(skip(more), Map.put(acc, key, val))
        "}" <> more -> {:ok, Map.put(acc, key, val), more}
        _ -> {:error, :invalid_json}
      end
    else
      false -> {:error, :invalid_json}
      error -> error
    end
  end

  defp array("]" <> rest, acc), do: {:ok, Enum.reverse(acc), rest}
  defp array(rest, acc) do
    with {:ok, val, after_value} <- value(rest) do
      case skip(after_value) do
        "," <> more -> array(skip(more), [val | acc])
        "]" <> more -> {:ok, Enum.reverse([val | acc]), more}
        _ -> {:error, :invalid_json}
      end
    end
  end

  defp string("\"" <> rest, acc), do: {:ok, acc, rest}
  defp string("\\\"" <> rest, acc), do: string(rest, acc <> "\"")
  defp string("\\\\" <> rest, acc), do: string(rest, acc <> "\\")
  defp string("\\n" <> rest, acc), do: string(rest, acc <> "\n")
  defp string("\\r" <> rest, acc), do: string(rest, acc <> "\r")
  defp string("\\t" <> rest, acc), do: string(rest, acc <> "\t")
  defp string("\\u" <> <<hex::binary-size(4), rest::binary>>, acc) do
    case Integer.parse(hex, 16) do
      {code, ""} -> string(rest, acc <> <<code::utf8>>)
      _ -> {:error, :invalid_json}
    end
  end
  defp string(<<char::utf8, rest::binary>>, acc) when char >= 0x20, do: string(rest, acc <> <<char::utf8>>)
  defp string(_, _), do: {:error, :invalid_json}

  defp skip(value), do: String.trim_leading(value)
end
