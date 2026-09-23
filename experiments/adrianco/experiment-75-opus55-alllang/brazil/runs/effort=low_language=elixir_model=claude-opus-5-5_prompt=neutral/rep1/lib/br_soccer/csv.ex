defmodule BrSoccer.CSV do
  @moduledoc "Minimal RFC4180-style CSV parser (quoted fields, escaped quotes, embedded commas)."

  @doc "Parses a file into a list of maps keyed by header names."
  def read_maps(path) do
    [header | rows] =
      path
      |> File.read!()
      |> strip_bom()
      |> parse()

    header = Enum.map(header, &String.trim/1)

    rows
    |> Enum.reject(&(&1 == [""]))
    |> Enum.map(fn row -> header |> Enum.zip(row) |> Map.new() end)
  end

  defp strip_bom(<<0xEF, 0xBB, 0xBF, rest::binary>>), do: rest
  defp strip_bom(bin), do: bin

  @doc "Parses CSV text into a list of rows (lists of strings)."
  def parse(bin), do: do_parse(bin, [], [], [])

  # do_parse(rest, field_iodata, row_acc, rows_acc)
  defp do_parse(<<>>, field, row, rows) do
    row = [field_str(field) | row]
    Enum.reverse(if row == [""], do: rows, else: [Enum.reverse(row) | rows])
  end

  defp do_parse(<<?", rest::binary>>, [], row, rows), do: quoted(rest, [], row, rows)
  defp do_parse(<<?,, rest::binary>>, field, row, rows), do: do_parse(rest, [], [field_str(field) | row], rows)

  defp do_parse(<<?\r, ?\n, rest::binary>>, field, row, rows), do: end_row(rest, field, row, rows)
  defp do_parse(<<?\n, rest::binary>>, field, row, rows), do: end_row(rest, field, row, rows)
  defp do_parse(<<c::utf8, rest::binary>>, field, row, rows), do: do_parse(rest, [field, <<c::utf8>>], row, rows)
  defp do_parse(<<c, rest::binary>>, field, row, rows), do: do_parse(rest, [field, c], row, rows)

  defp end_row(rest, field, row, rows) do
    do_parse(rest, [], [], [Enum.reverse([field_str(field) | row]) | rows])
  end

  defp quoted(<<?", ?", rest::binary>>, field, row, rows), do: quoted(rest, [field, ?"], row, rows)
  defp quoted(<<?", rest::binary>>, field, row, rows), do: do_parse(rest, [field, ""], row, rows)
  defp quoted(<<c, rest::binary>>, field, row, rows), do: quoted(rest, [field, c], row, rows)
  defp quoted(<<>>, field, row, rows), do: do_parse(<<>>, field, row, rows)

  defp field_str(field), do: IO.iodata_to_binary(field)
end
