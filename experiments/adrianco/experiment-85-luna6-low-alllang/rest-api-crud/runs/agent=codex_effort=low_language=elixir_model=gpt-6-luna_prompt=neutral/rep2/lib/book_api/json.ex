defmodule BookApi.JSON do
  @moduledoc "A small JSON encoder and decoder for this dependency-free service."

  def encode(value), do: value |> encode_value() |> IO.iodata_to_binary()

  def decode(binary) when is_binary(binary) do
    with {:ok, value, rest} <- parse_value(skip_ws(binary)), true <- skip_ws(rest) == <<>> do
      {:ok, value}
    else
      _ -> {:error, :invalid_json}
    end
  rescue
    _ -> {:error, :invalid_json}
  end

  defp encode_value(nil), do: "null"
  defp encode_value(true), do: "true"
  defp encode_value(false), do: "false"
  defp encode_value(n) when is_integer(n), do: Integer.to_string(n)
  defp encode_value(n) when is_float(n), do: Float.to_string(n)
  defp encode_value(s) when is_binary(s), do: ["\"", escape(s), "\""]

  defp encode_value(list) when is_list(list),
    do: ["[", Enum.intersperse(Enum.map(list, &encode_value/1), ","), "]"]

  defp encode_value(map) when is_map(map) do
    pairs = Enum.map(map, fn {k, v} -> [encode_value(to_string(k)), ":", encode_value(v)] end)
    ["{", Enum.intersperse(pairs, ","), "}"]
  end

  defp escape(s) do
    for <<c::utf8 <- s>>, into: "" do
      case c do
        ?" -> "\\\""
        ?\\ -> "\\\\"
        ?\b -> "\\b"
        ?\f -> "\\f"
        ?\n -> "\\n"
        ?\r -> "\\r"
        ?\t -> "\\t"
        c when c < 0x20 -> "\\u" <> (c |> Integer.to_string(16) |> String.pad_leading(4, "0"))
        c -> <<c::utf8>>
      end
    end
  end

  defp skip_ws(<<c, rest::binary>>) when c in [32, 9, 10, 13], do: skip_ws(rest)
  defp skip_ws(s), do: s
  defp parse_value(<<"null", rest::binary>>), do: {:ok, nil, rest}
  defp parse_value(<<"true", rest::binary>>), do: {:ok, true, rest}
  defp parse_value(<<"false", rest::binary>>), do: {:ok, false, rest}
  defp parse_value(<<"\"", rest::binary>>), do: parse_string(rest, "")
  defp parse_value(<<"{", rest::binary>>), do: parse_object(skip_ws(rest), %{})
  defp parse_value(<<"[", rest::binary>>), do: parse_array(skip_ws(rest), [])
  defp parse_value(<<c, _::binary>> = s) when c == ?- or c in ?0..?9, do: parse_number(s)
  defp parse_value(_), do: {:error, :invalid_json}

  defp parse_string(<<"\"", rest::binary>>, acc), do: {:ok, acc, rest}
  defp parse_string(<<"\\\"", rest::binary>>, acc), do: parse_string(rest, acc <> "\"")
  defp parse_string(<<"\\\\", rest::binary>>, acc), do: parse_string(rest, acc <> "\\")
  defp parse_string(<<"\\/", rest::binary>>, acc), do: parse_string(rest, acc <> "/")
  defp parse_string(<<"\\b", rest::binary>>, acc), do: parse_string(rest, acc <> <<8>>)
  defp parse_string(<<"\\f", rest::binary>>, acc), do: parse_string(rest, acc <> <<12>>)
  defp parse_string(<<"\\n", rest::binary>>, acc), do: parse_string(rest, acc <> "\n")
  defp parse_string(<<"\\r", rest::binary>>, acc), do: parse_string(rest, acc <> "\r")
  defp parse_string(<<"\\t", rest::binary>>, acc), do: parse_string(rest, acc <> "\t")

  defp parse_string(<<"\\u", hex::binary-size(4), rest::binary>>, acc) do
    code = String.to_integer(hex, 16)
    parse_string(rest, acc <> <<code::utf8>>)
  end

  defp parse_string(<<c::utf8, rest::binary>>, acc) when c >= 0x20,
    do: parse_string(rest, acc <> <<c::utf8>>)

  defp parse_string(_, _), do: {:error, :invalid_json}

  defp parse_object(<<"}", rest::binary>>, map), do: {:ok, map, rest}

  defp parse_object(<<"\"", rest::binary>>, map) do
    with {:ok, key, rest} <- parse_string(rest, ""),
         <<":", rest::binary>> <- skip_ws(rest),
         {:ok, value, rest} <- parse_value(skip_ws(rest)) do
      case skip_ws(rest) do
        <<",", rest::binary>> -> parse_object(skip_ws(rest), Map.put(map, key, value))
        <<"}", rest::binary>> -> {:ok, Map.put(map, key, value), rest}
        _ -> {:error, :invalid_json}
      end
    else
      _ -> {:error, :invalid_json}
    end
  end

  defp parse_object(_, _), do: {:error, :invalid_json}
  defp parse_array(<<"]", rest::binary>>, acc), do: {:ok, Enum.reverse(acc), rest}

  defp parse_array(binary, acc) do
    with {:ok, value, rest} <- parse_value(binary) do
      case skip_ws(rest) do
        <<",", rest::binary>> -> parse_array(skip_ws(rest), [value | acc])
        <<"]", rest::binary>> -> {:ok, Enum.reverse([value | acc]), rest}
        _ -> {:error, :invalid_json}
      end
    end
  end

  defp parse_number(binary) do
    case Regex.run(~r/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/, binary) do
      [number] ->
        rest = binary_part(binary, byte_size(number), byte_size(binary) - byte_size(number))

        value =
          if String.contains?(number, [".", "e", "E"]),
            do: String.to_float(number),
            else: String.to_integer(number)

        {:ok, value, rest}

      _ ->
        {:error, :invalid_json}
    end
  end
end
