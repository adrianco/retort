defmodule BrazilianSoccer.JSON do
  @moduledoc false
  def decode!(text) do
    {value, rest} = value(skip(text))
    if skip(rest) == "", do: value, else: raise(ArgumentError, "invalid JSON")
  end

  def encode(value), do: encode_value(value)
  defp value(<<"{", rest::binary>>), do: object(skip(rest), %{})
  defp value(<<"[", rest::binary>>), do: array(skip(rest), [])
  defp value(<<"\"", rest::binary>>), do: string(rest, "")
  defp value(<<"true", rest::binary>>), do: {true, rest}
  defp value(<<"false", rest::binary>>), do: {false, rest}
  defp value(<<"null", rest::binary>>), do: {nil, rest}
  defp value(text), do: number(text)
  defp object(<<"}", rest::binary>>, map), do: {map, rest}

  defp object(<<"\"", rest::binary>>, map) do
    {key, rest} = string(rest, "")
    <<":", rest::binary>> = skip(rest)
    {val, rest} = value(skip(rest))
    rest = skip(rest)

    case rest do
      <<",", next::binary>> -> object(skip(next), Map.put(map, key, val))
      <<"}", next::binary>> -> {Map.put(map, key, val), next}
      _ -> raise ArgumentError, "invalid object"
    end
  end

  defp array(<<"]", rest::binary>>, values), do: {Enum.reverse(values), rest}

  defp array(text, values) do
    {val, rest} = value(text)
    rest = skip(rest)

    case rest do
      <<",", next::binary>> -> array(skip(next), [val | values])
      <<"]", next::binary>> -> {Enum.reverse([val | values]), next}
      _ -> raise ArgumentError, "invalid array"
    end
  end

  defp string(<<"\"", rest::binary>>, acc), do: {acc, rest}

  defp string(<<"\\", char, rest::binary>>, acc) when char in ~c"\"\\/",
    do: string(rest, acc <> <<char>>)

  defp string(<<"\\n", rest::binary>>, acc), do: string(rest, acc <> "\n")
  defp string(<<"\\r", rest::binary>>, acc), do: string(rest, acc <> "\r")
  defp string(<<"\\t", rest::binary>>, acc), do: string(rest, acc <> "\t")
  defp string(<<char::utf8, rest::binary>>, acc), do: string(rest, acc <> <<char::utf8>>)

  defp number(text) do
    {token, rest} = take_number(text, "")

    case Integer.parse(token) do
      {n, ""} ->
        {n, rest}

      _ ->
        {n, ""} = Float.parse(token)
        {n, rest}
    end
  end

  defp take_number(<<char, rest::binary>>, acc) when char in ~c"-+0123456789.eE",
    do: take_number(rest, acc <> <<char>>)

  defp take_number(rest, acc), do: {acc, rest}
  defp skip(<<char, rest::binary>>) when char in ~c" \n\r\t", do: skip(rest)
  defp skip(text), do: text
  defp encode_value(nil), do: "null"
  defp encode_value(true), do: "true"
  defp encode_value(false), do: "false"
  defp encode_value(n) when is_integer(n) or is_float(n), do: to_string(n)
  defp encode_value(%Date{} = date), do: encode_value(Date.to_iso8601(date))

  defp encode_value(value) when is_binary(value),
    do:
      "\"" <>
        (value
         |> String.replace("\\", "\\\\")
         |> String.replace("\"", "\\\"")
         |> String.replace("\n", "\\n")
         |> String.replace("\r", "\\r")) <> "\""

  defp encode_value(value) when is_list(value),
    do: "[" <> Enum.map_join(value, ",", &encode_value/1) <> "]"

  defp encode_value(value) when is_map(value),
    do:
      "{" <>
        Enum.map_join(value, ",", fn {k, v} ->
          encode_value(to_string(k)) <> ":" <> encode_value(v)
        end) <> "}"
end
