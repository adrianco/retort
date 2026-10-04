defmodule BrazilianSoccer.CSV do
  @moduledoc """
  Minimal RFC 4180 CSV parser (quoted fields, escaped quotes, embedded
  commas/newlines, CRLF line endings and a leading UTF-8 BOM).
  """

  @doc "Parses a CSV binary into a list of rows (lists of strings)."
  def parse(<<0xEF, 0xBB, 0xBF, rest::binary>>), do: parse(rest)
  def parse(bin) when is_binary(bin), do: field(bin, [], [], [])

  @doc "Parses a CSV binary into a list of maps keyed by the header row."
  def parse_maps(bin) do
    case parse(bin) do
      [] ->
        []

      [header | rows] ->
        header = Enum.map(header, &String.trim/1)
        Enum.map(rows, fn row -> header |> Enum.zip(row) |> Map.new() end)
    end
  end

  # field/4: start of a field. acc = iodata of the current field (reversed),
  # row = fields of current row (reversed), rows = finished rows (reversed).
  defp field(<<?", rest::binary>>, _acc, row, rows), do: quoted(rest, [], row, rows)
  defp field(bin, _acc, row, rows), do: plain(bin, 0, bin, row, rows)

  defp plain(bin, len, orig, row, rows) do
    case bin do
      <<?,, rest::binary>> ->
        field(rest, [], [binary_part(orig, 0, len) | row], rows)

      <<?\r, ?\n, rest::binary>> ->
        end_row(rest, [binary_part(orig, 0, len) | row], rows)

      <<?\n, rest::binary>> ->
        end_row(rest, [binary_part(orig, 0, len) | row], rows)

      <<_, rest::binary>> ->
        plain(rest, len + 1, orig, row, rows)

      <<>> ->
        finish([binary_part(orig, 0, len) | row], rows)
    end
  end

  defp quoted(<<?", ?", rest::binary>>, acc, row, rows), do: quoted(rest, [?" | acc], row, rows)
  defp quoted(<<?", rest::binary>>, acc, row, rows), do: after_quote(rest, acc, row, rows)
  defp quoted(<<c, rest::binary>>, acc, row, rows), do: quoted(rest, [c | acc], row, rows)
  defp quoted(<<>>, acc, row, rows), do: finish([to_bin(acc) | row], rows)

  defp after_quote(<<?,, rest::binary>>, acc, row, rows),
    do: field(rest, [], [to_bin(acc) | row], rows)

  defp after_quote(<<?\r, ?\n, rest::binary>>, acc, row, rows),
    do: end_row(rest, [to_bin(acc) | row], rows)

  defp after_quote(<<?\n, rest::binary>>, acc, row, rows),
    do: end_row(rest, [to_bin(acc) | row], rows)

  defp after_quote(<<>>, acc, row, rows), do: finish([to_bin(acc) | row], rows)
  # Stray characters after a closing quote are kept as part of the field.
  defp after_quote(<<c, rest::binary>>, acc, row, rows),
    do: after_quote(rest, [c | acc], row, rows)

  defp end_row(<<>>, row, rows), do: Enum.reverse([Enum.reverse(row) | rows])
  defp end_row(rest, row, rows), do: field(rest, [], [], [Enum.reverse(row) | rows])

  defp finish([""], rows), do: Enum.reverse(rows)
  defp finish(row, rows), do: Enum.reverse([Enum.reverse(row) | rows])

  defp to_bin(acc), do: acc |> Enum.reverse() |> IO.iodata_to_binary()
end
