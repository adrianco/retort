defmodule BrazilianSoccerMcp.CSV do
  @moduledoc """
  Minimal RFC 4180 CSV parser (no external dependencies).

  Handles quoted fields (including embedded commas, newlines, and escaped
  quotes), CRLF and LF line endings, and a leading UTF-8 BOM.
  """

  @doc "Parse a CSV file into a list of rows (each row a list of string fields)."
  def parse_file(path) do
    path |> File.read!() |> parse()
  end

  @doc "Parse a CSV file into a list of maps keyed by the header row."
  def parse_file_to_maps(path) do
    path |> parse_file() |> rows_to_maps()
  end

  @doc "Parse a CSV binary into a list of rows."
  def parse(binary) do
    binary
    |> strip_bom()
    |> unquoted("", [], [])
  end

  @doc "Convert `[header | rows]` into a list of maps keyed by header fields."
  def rows_to_maps([]), do: []

  def rows_to_maps([header | rows]) do
    for row <- rows, row != [""] do
      header |> Enum.zip(row) |> Map.new()
    end
  end

  defp strip_bom(<<0xEF, 0xBB, 0xBF, rest::binary>>), do: rest
  defp strip_bom(bin), do: bin

  # State: outside quotes. A quote only opens quoted mode at field start.
  defp unquoted(<<?", rest::binary>>, "", fields, rows), do: quoted(rest, "", fields, rows)

  defp unquoted(<<?,, rest::binary>>, field, fields, rows),
    do: unquoted(rest, "", [field | fields], rows)

  defp unquoted(<<?\r, ?\n, rest::binary>>, field, fields, rows),
    do: end_row(rest, field, fields, rows)

  defp unquoted(<<?\n, rest::binary>>, field, fields, rows),
    do: end_row(rest, field, fields, rows)

  defp unquoted(<<c, rest::binary>>, field, fields, rows),
    do: unquoted(rest, <<field::binary, c>>, fields, rows)

  defp unquoted(<<>>, "", [], rows), do: Enum.reverse(rows)
  defp unquoted(<<>>, field, fields, rows), do: Enum.reverse([end_fields(field, fields) | rows])

  # State: inside a quoted field. "" is an escaped quote.
  defp quoted(<<?", ?", rest::binary>>, field, fields, rows),
    do: quoted(rest, <<field::binary, ?">>, fields, rows)

  defp quoted(<<?", rest::binary>>, field, fields, rows), do: unquoted(rest, field, fields, rows)

  defp quoted(<<c, rest::binary>>, field, fields, rows),
    do: quoted(rest, <<field::binary, c>>, fields, rows)

  defp quoted(<<>>, field, fields, rows), do: unquoted(<<>>, field, fields, rows)

  defp end_row(rest, field, fields, rows),
    do: unquoted(rest, "", [], [end_fields(field, fields) | rows])

  defp end_fields(field, fields), do: Enum.reverse([field | fields])
end
