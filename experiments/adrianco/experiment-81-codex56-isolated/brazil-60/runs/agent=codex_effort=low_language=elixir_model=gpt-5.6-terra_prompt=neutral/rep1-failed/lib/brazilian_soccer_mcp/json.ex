defmodule BrazilianSoccerMcp.JSON do
  @moduledoc false
  def encode(value), do: IO.iodata_to_binary(enc(value))

  defp enc(map) when is_map(map),
    do: [
      "{",
      Enum.intersperse(Enum.map(map, fn {k, v} -> [enc(to_string(k)), ":", enc(v)] end), ","),
      "}"
    ]

  defp enc(list) when is_list(list), do: ["[", Enum.intersperse(Enum.map(list, &enc/1), ","), "]"]

  defp enc(value) when is_binary(value),
    do: [
      "\"",
      String.replace(value, ~r/[\\\"\n\r\t]/, fn
        "\\" -> "\\\\"
        "\"" -> "\\\""
        "\n" -> "\\n"
        "\r" -> "\\r"
        "\t" -> "\\t"
      end),
      "\""
    ]

  defp enc(value) when is_boolean(value), do: to_string(value)
  defp enc(nil), do: "null"
  defp enc(value), do: to_string(value)

  def decode(text) do
    with {:ok, value, rest} <- value(String.trim(text)),
         true <- String.trim(rest) == "" do
      {:ok, value}
    else
      _ -> {:error, :invalid_json}
    end
  end

  defp value(<<"{", rest::binary>>), do: object(String.trim_leading(rest), %{})
  defp value(<<"[", rest::binary>>), do: array(String.trim_leading(rest), [])
  defp value(<<"\"", rest::binary>>), do: string(rest, "")
  defp value(<<"true", rest::binary>>), do: {:ok, true, rest}
  defp value(<<"false", rest::binary>>), do: {:ok, false, rest}
  defp value(<<"null", rest::binary>>), do: {:ok, nil, rest}

  defp value(text) do
    case Float.parse(text) do
      {n, rest} -> {:ok, if(n == trunc(n), do: trunc(n), else: n), rest}
      _ -> {:error, :invalid_json}
    end
  end

  defp object(<<"}", rest::binary>>, acc), do: {:ok, acc, rest}

  defp object(<<"\"", rest::binary>>, acc) do
    with {:ok, key, rest} <- string(rest, ""),
         <<":", rest::binary>> <- String.trim_leading(rest),
         {:ok, val, rest} <- value(String.trim_leading(rest)) do
      case String.trim_leading(rest) do
        <<"}", r::binary>> -> {:ok, Map.put(acc, key, val), r}
        <<",", r::binary>> -> object(String.trim_leading(r), Map.put(acc, key, val))
        _ -> {:error, :invalid_json}
      end
    else
      _ -> {:error, :invalid_json}
    end
  end

  defp object(_, _), do: {:error, :invalid_json}
  defp array(<<"]", rest::binary>>, acc), do: {:ok, Enum.reverse(acc), rest}

  defp array(text, acc) do
    with {:ok, val, rest} <- value(text) do
      case String.trim_leading(rest) do
        <<"]", r::binary>> -> {:ok, Enum.reverse([val | acc]), r}
        <<",", r::binary>> -> array(String.trim_leading(r), [val | acc])
        _ -> {:error, :invalid_json}
      end
    end
  end

  defp string(<<"\"", rest::binary>>, acc), do: {:ok, acc, rest}

  defp string(<<"\\", c::utf8, rest::binary>>, acc),
    do:
      string(
        rest,
        acc <>
          case c do
            ?n -> "\n"
            ?r -> "\r"
            ?t -> "\t"
            x -> <<x::utf8>>
          end
      )

  defp string(<<c::utf8, rest::binary>>, acc), do: string(rest, acc <> <<c::utf8>>)
  defp string(_, _), do: {:error, :invalid_json}
end
