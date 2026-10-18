defmodule BookApi.JSON do
  @moduledoc "Small JSON encoder/parser for the dependency-free HTTP service."
  def encode(value), do: value |> encode_value() |> IO.iodata_to_binary()
  def decode(binary) do
    case parse_value(skip_ws(binary)) do
      {:ok, value, rest} -> if skip_ws(rest) == "", do: {:ok, value}, else: {:error, :invalid_json}
      _ -> {:error, :invalid_json}
    end
  end

  defp encode_value(nil), do: "null"
  defp encode_value(true), do: "true"
  defp encode_value(false), do: "false"
  defp encode_value(n) when is_number(n), do: to_string(n)
  defp encode_value(s) when is_binary(s), do: ["\"", escape(s), "\""]
  defp encode_value(list) when is_list(list), do: ["[", Enum.intersperse(Enum.map(list, &encode_value/1), ","), "]"]
  defp encode_value(map) when is_map(map), do: ["{", Enum.intersperse(Enum.map(map, fn {k, v} -> [encode_value(to_string(k)), ":", encode_value(v)] end), ","), "}"]

  defp escape(s) do
    for <<c::utf8 <- s>>, into: "" do
      case c do
        ?" -> "\\\""
        ?\\ -> "\\\\"
        ?\n -> "\\n"
        ?\r -> "\\r"
        ?\t -> "\\t"
        c when c < 32 -> "\\u" <> (c |> Integer.to_string(16) |> String.pad_leading(4, "0"))
        _ -> <<c::utf8>>
      end
    end
  end

  defp parse_value(<<"null", rest::binary>>), do: {:ok, nil, rest}
  defp parse_value(<<"true", rest::binary>>), do: {:ok, true, rest}
  defp parse_value(<<"false", rest::binary>>), do: {:ok, false, rest}
  defp parse_value(<<"\"", rest::binary>>), do: parse_string(rest, "")
  defp parse_value(<<"[", rest::binary>>), do: parse_array(skip_ws(rest), [])
  defp parse_value(<<"{", rest::binary>>), do: parse_object(skip_ws(rest), %{})
  defp parse_value(binary), do: parse_number(binary)

  defp parse_string(<<"\"", rest::binary>>, acc), do: {:ok, acc, rest}
  defp parse_string(<<"\\\"", rest::binary>>, acc), do: parse_string(rest, acc <> "\"")
  defp parse_string(<<"\\\\", rest::binary>>, acc), do: parse_string(rest, acc <> "\\")
  defp parse_string(<<"\\n", rest::binary>>, acc), do: parse_string(rest, acc <> "\n")
  defp parse_string(<<"\\r", rest::binary>>, acc), do: parse_string(rest, acc <> "\r")
  defp parse_string(<<"\\t", rest::binary>>, acc), do: parse_string(rest, acc <> "\t")
  defp parse_string(<<c::utf8, rest::binary>>, acc) when c >= 32, do: parse_string(rest, acc <> <<c::utf8>>)
  defp parse_string(_, _), do: {:error, :invalid_string}

  defp parse_array(<<"]", rest::binary>>, acc), do: {:ok, Enum.reverse(acc), rest}
  defp parse_array(binary, acc) do
    with {:ok, value, rest} <- parse_value(binary) do
      case skip_ws(rest) do
        <<",", tail::binary>> -> parse_array(skip_ws(tail), [value | acc])
        <<"]", tail::binary>> -> {:ok, Enum.reverse([value | acc]), tail}
        _ -> {:error, :invalid_array}
      end
    end
  end

  defp parse_object(<<"}", rest::binary>>, acc), do: {:ok, acc, rest}
  defp parse_object(<<"\"", rest::binary>>, acc) do
    with {:ok, key, tail} <- parse_string(rest, ""), <<":", value_tail::binary>> <- skip_ws(tail),
         {:ok, value, after_value} <- parse_value(skip_ws(value_tail)) do
      case skip_ws(after_value) do
        <<",", more::binary>> -> parse_object(skip_ws(more), Map.put(acc, key, value))
        <<"}", more::binary>> -> {:ok, Map.put(acc, key, value), more}
        _ -> {:error, :invalid_object}
      end
    else
      _ -> {:error, :invalid_object}
    end
  end
  defp parse_object(_, _), do: {:error, :invalid_object}

  defp parse_number(binary) do
    case Regex.run(~r/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/, binary) do
      [number] ->
        value = if String.contains?(number, [".", "e", "E"]), do: Float.parse(number) |> elem(0), else: String.to_integer(number)
        {:ok, value, binary_part(binary, byte_size(number), byte_size(binary) - byte_size(number))}
      _ -> {:error, :invalid_value}
    end
  end

  defp skip_ws(<<c, rest::binary>>) when c in [32, 9, 10, 13], do: skip_ws(rest)
  defp skip_ws(binary), do: binary
end
