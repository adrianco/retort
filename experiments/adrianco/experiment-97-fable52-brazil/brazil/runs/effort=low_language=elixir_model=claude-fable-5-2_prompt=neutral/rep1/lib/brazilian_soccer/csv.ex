defmodule BrazilianSoccer.CSV do
  @moduledoc "Small RFC 4180 CSV parser (quoted fields, escaped quotes, CRLF, UTF-8 BOM)."

  @doc "Parses CSV text into a list of rows (lists of strings)."
  def parse(<<0xEF, 0xBB, 0xBF, rest::binary>>), do: parse(rest)
  def parse(bin) when is_binary(bin), do: start(bin, [], [])

  @doc "Parses CSV text into maps keyed by the header row."
  def parse_maps(bin) do
    case parse(bin) do
      [] ->
        []

      [header | rows] ->
        header = Enum.map(header, &String.trim/1)
        Enum.map(rows, fn row -> header |> Enum.zip(row) |> Map.new() end)
    end
  end

  def read_maps!(path), do: path |> File.read!() |> parse_maps()

  # At the start of a field.
  defp start(<<>>, [], rows), do: Enum.reverse(rows)
  defp start(<<>>, row, rows), do: Enum.reverse([Enum.reverse(["" | row]) | rows])
  defp start(<<?", rest::binary>>, row, rows), do: quoted(rest, "", row, rows)
  defp start(bin, row, rows), do: unquoted(bin, "", row, rows)

  defp unquoted(<<?,, rest::binary>>, acc, row, rows), do: start(rest, [acc | row], rows)
  defp unquoted(<<?\r, ?\n, rest::binary>>, acc, row, rows), do: end_row(rest, acc, row, rows)
  defp unquoted(<<?\n, rest::binary>>, acc, row, rows), do: end_row(rest, acc, row, rows)
  defp unquoted(<<>>, acc, row, rows), do: end_row(<<>>, acc, row, rows)

  defp unquoted(<<c, rest::binary>>, acc, row, rows),
    do: unquoted(rest, <<acc::binary, c>>, row, rows)

  defp quoted(<<?", ?", rest::binary>>, acc, row, rows),
    do: quoted(rest, <<acc::binary, ?">>, row, rows)

  defp quoted(<<?", rest::binary>>, acc, row, rows), do: unquoted(rest, acc, row, rows)
  defp quoted(<<>>, acc, row, rows), do: end_row(<<>>, acc, row, rows)

  defp quoted(<<c, rest::binary>>, acc, row, rows),
    do: quoted(rest, <<acc::binary, c>>, row, rows)

  # Blank lines are skipped.
  defp end_row(rest, "", [], rows), do: start(rest, [], rows)
  defp end_row(rest, acc, row, rows), do: start(rest, [], [Enum.reverse([acc | row]) | rows])
end
