defmodule BrazilianSoccerMcp.JSON do
  @moduledoc false
  def encode(value), do: IO.iodata_to_binary(value |> encode_value())

  def decode(string) when is_binary(string) do
    with {:ok, value, rest} <- value(skip(String.to_charlist(string))),
         true <- skip(rest) == [] do
      {:ok, value}
    else
      _ -> {:error, :invalid_json}
    end
  end

  defp encode_value(nil), do: "null"
  defp encode_value(true), do: "true"
  defp encode_value(false), do: "false"

  defp encode_value(value) when is_binary(value),
    do: [
      "\"",
      escape(value),
      "\""
    ]

  defp encode_value(value) when is_atom(value), do: encode_value(Atom.to_string(value))
  defp encode_value(value) when is_integer(value) or is_float(value), do: to_string(value)

  defp encode_value(value) when is_list(value),
    do: ["[", Enum.intersperse(Enum.map(value, &encode_value/1), ","), "]"]

  defp encode_value(value) when is_map(value),
    do: [
      "{",
      Enum.intersperse(
        Enum.map(value, fn {key, val} ->
          [encode_value(to_string(key)), ":", encode_value(val)]
        end),
        ","
      ),
      "}"
    ]

  defp escape(value) do
    Enum.reduce(
      [{"\\", "\\\\"}, {"\"", "\\\""}, {"\n", "\\n"}, {"\r", "\\r"}, {"\t", "\\t"}],
      value,
      fn {from, to}, acc -> String.replace(acc, from, to) end
    )
  end

  defp value([?" | rest]), do: string(rest, [])
  defp value([?{ | rest]), do: object(skip(rest), %{})
  defp value([?[ | rest]), do: array(skip(rest), [])
  defp value(~c"true" ++ rest), do: {:ok, true, rest}
  defp value(~c"false" ++ rest), do: {:ok, false, rest}
  defp value(~c"null" ++ rest), do: {:ok, nil, rest}
  defp value(chars), do: number(chars)
  defp string([], _), do: {:error, :unterminated_string}
  defp string([?" | rest], acc), do: {:ok, acc |> Enum.reverse() |> List.to_string(), rest}
  defp string([?\\, escape | rest], acc), do: string(rest, [escape_char(escape) | acc])
  defp string([char | rest], acc), do: string(rest, [char | acc])
  defp escape_char(?n), do: ?\n
  defp escape_char(?r), do: ?\r
  defp escape_char(?t), do: ?\t
  defp escape_char(char), do: char
  defp object([?} | rest], acc), do: {:ok, acc, rest}

  defp object(chars, acc) do
    with {:ok, key, [?\: | rest]} <- value(chars), {:ok, val, rest} <- value(skip(rest)) do
      case skip(rest) do
        [?, | next] -> object(skip(next), Map.put(acc, key, val))
        [?} | next] -> {:ok, Map.put(acc, key, val), next}
        _ -> {:error, :bad_object}
      end
    end
  end

  defp array([?] | rest], acc), do: {:ok, Enum.reverse(acc), rest}

  defp array(chars, acc) do
    with {:ok, val, rest} <- value(chars) do
      case skip(rest) do
        [?, | next] -> array(skip(next), [val | acc])
        [?] | next] -> {:ok, Enum.reverse([val | acc]), next}
        _ -> {:error, :bad_array}
      end
    end
  end

  defp number(chars) do
    {digits, rest} = Enum.split_while(chars, &(&1 in ~c"0123456789+-.eE"))

    case Float.parse(List.to_string(digits)) do
      {number, ""} -> {:ok, if(number == trunc(number), do: trunc(number), else: number), rest}
      _ -> {:error, :bad_number}
    end
  end

  defp skip([char | rest]) when char in [32, 9, 10, 13], do: skip(rest)
  defp skip(chars), do: chars
end
