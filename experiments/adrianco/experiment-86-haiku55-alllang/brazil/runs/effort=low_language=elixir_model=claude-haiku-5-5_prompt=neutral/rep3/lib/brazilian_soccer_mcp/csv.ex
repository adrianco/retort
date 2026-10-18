defmodule BrazilianSoccerMcp.CSV do
  @moduledoc """
  Minimal RFC 4180 CSV parser.

  Handles quoted fields (with `""` escapes and embedded delimiters or
  newlines), LF and CRLF line endings, and a leading UTF-8 byte order mark.
  Input is treated as raw UTF-8 bytes; nothing is transcoded.
  """

  @doc "Parses CSV text into rows of field strings, skipping blank lines."
  @spec parse(binary()) :: [[binary()]]
  def parse(text) when is_binary(text) do
    text
    |> strip_bom()
    |> rows()
    |> Enum.reject(&(&1 == [""]))
  end

  @doc "Parses CSV text into one map per data row, keyed by the header row."
  @spec parse_maps(binary()) :: [%{binary() => binary()}]
  def parse_maps(text) do
    case parse(text) do
      [] -> []
      [header | rows] -> Enum.map(rows, &(header |> Enum.zip(&1) |> Map.new()))
    end
  end

  defp strip_bom(<<0xEF, 0xBB, 0xBF, rest::binary>>), do: rest
  defp strip_bom(text), do: text

  defp rows(""), do: []

  defp rows(input) do
    {fields, rest} = record(input, [])
    [fields | rows(rest)]
  end

  defp record(input, fields) do
    {field, rest} = field(input)
    fields = [field | fields]

    case rest do
      <<",", more::binary>> -> record(more, fields)
      <<"\r\n", more::binary>> -> {Enum.reverse(fields), more}
      <<"\n", more::binary>> -> {Enum.reverse(fields), more}
      <<"\r", more::binary>> -> {Enum.reverse(fields), more}
      "" -> {Enum.reverse(fields), ""}
    end
  end

  defp field(<<?", rest::binary>>), do: quoted(rest, [])
  defp field(input), do: unquoted(input, [])

  defp unquoted(<<c, rest::binary>>, acc) when c not in [?,, ?\n, ?\r],
    do: unquoted(rest, [c | acc])

  defp unquoted(rest, acc), do: {to_binary(acc), rest}

  defp quoted(<<?", ?", rest::binary>>, acc), do: quoted(rest, [?" | acc])
  defp quoted(<<?", rest::binary>>, acc), do: {to_binary(acc), skip_to_delimiter(rest)}
  defp quoted(<<c, rest::binary>>, acc), do: quoted(rest, [c | acc])
  defp quoted(<<>>, acc), do: {to_binary(acc), ""}

  # Tolerates stray characters after a closing quote, as many exporters emit them.
  defp skip_to_delimiter(<<c, rest::binary>>) when c not in [?,, ?\n, ?\r],
    do: skip_to_delimiter(rest)

  defp skip_to_delimiter(rest), do: rest

  defp to_binary(reversed_bytes), do: reversed_bytes |> Enum.reverse() |> :erlang.list_to_binary()
end
