defmodule BrazilianSoccer.CSV do
  @moduledoc """
  Minimal RFC 4180 CSV reader.

  Handles a leading UTF-8 byte-order mark, `\\n` and `\\r\\n` line endings, and
  quoted fields containing commas, newlines and doubled quotes (`""`).
  Field values are returned as strings; no type conversion is done.
  """

  @bom <<0xEF, 0xBB, 0xBF>>

  @doc "Parses CSV text into a list of rows, each a list of field strings."
  @spec parse_rows(binary()) :: [[binary()]]
  def parse_rows(content) when is_binary(content) do
    content
    |> strip_bom()
    |> parse(false, "", [], [])
  end

  @doc """
  Parses CSV text whose first row is a header. Returns one map per data row,
  keyed by trimmed header name. Blank lines are skipped; short rows are padded
  with empty strings.
  """
  @spec parse_with_headers(binary()) :: [%{binary() => binary()}]
  def parse_with_headers(content) do
    case parse_rows(content) do
      [] ->
        []

      [header | rows] ->
        keys = Enum.map(header, &String.trim/1)
        for row <- rows, row != [""], do: row_to_map(keys, row)
    end
  end

  defp row_to_map(keys, row) do
    padding = List.duplicate("", max(length(keys) - length(row), 0))
    keys |> Enum.zip(row ++ padding) |> Map.new()
  end

  defp strip_bom(@bom <> rest), do: rest
  defp strip_bom(content), do: content

  # Inside a quoted field
  defp parse(<<?", ?", rest::binary>>, true, field, row, acc),
    do: parse(rest, true, field <> "\"", row, acc)

  defp parse(<<?", rest::binary>>, true, field, row, acc),
    do: parse(rest, false, field, row, acc)

  defp parse(<<c, rest::binary>>, true, field, row, acc),
    do: parse(rest, true, field <> <<c>>, row, acc)

  # Outside a quoted field
  defp parse(<<?", rest::binary>>, false, field, row, acc),
    do: parse(rest, true, field, row, acc)

  defp parse(<<?,, rest::binary>>, false, field, row, acc),
    do: parse(rest, false, "", [field | row], acc)

  defp parse(<<?\r, ?\n, rest::binary>>, false, field, row, acc),
    do: parse(rest, false, "", [], [end_row(field, row) | acc])

  defp parse(<<?\n, rest::binary>>, false, field, row, acc),
    do: parse(rest, false, "", [], [end_row(field, row) | acc])

  defp parse(<<c, rest::binary>>, false, field, row, acc),
    do: parse(rest, false, field <> <<c>>, row, acc)

  # End of input
  defp parse(<<>>, _in_quotes, "", [], acc), do: Enum.reverse(acc)
  defp parse(<<>>, _in_quotes, field, row, acc), do: Enum.reverse([end_row(field, row) | acc])

  defp end_row(field, row), do: Enum.reverse([field | row])
end
