defmodule SoccerMcp.CSV do
  @moduledoc """
  Minimal RFC 4180 CSV reader.

  Handles a UTF-8 byte order mark, LF and CRLF line endings, quoted fields
  containing commas or newlines, and doubled quotes inside quoted fields.

  `parse/1` returns one map per data row, keyed by the header row.
  """

  @spec parse(binary()) :: [map()]
  def parse(binary) when is_binary(binary) do
    case binary |> strip_bom() |> records() |> Enum.reject(&blank?/1) do
      [] ->
        []

      [header | rows] ->
        Enum.map(rows, fn row -> header |> Enum.zip(row) |> Map.new() end)
    end
  end

  @doc "Reads and parses a CSV file from disk."
  @spec parse_file(Path.t()) :: [map()]
  def parse_file(path), do: path |> File.read!() |> parse()

  defp strip_bom(<<0xEF, 0xBB, 0xBF, rest::binary>>), do: rest
  defp strip_bom(binary), do: binary

  defp records(""), do: []

  defp records(bin) do
    {row, rest} = field(bin, [], "")
    [row | records(rest)]
  end

  defp blank?(row), do: Enum.all?(row, &(&1 == ""))

  # Start of a field: a leading quote switches to quoted mode.
  defp field(<<?", rest::binary>>, acc, ""), do: quoted(rest, acc, "")
  defp field(<<?,, rest::binary>>, acc, cur), do: field(rest, [cur | acc], "")
  defp field(<<"\r\n", rest::binary>>, acc, cur), do: {Enum.reverse([cur | acc]), rest}
  defp field(<<?\n, rest::binary>>, acc, cur), do: {Enum.reverse([cur | acc]), rest}
  defp field(<<c, rest::binary>>, acc, cur), do: field(rest, acc, cur <> <<c>>)
  defp field(<<>>, acc, cur), do: {Enum.reverse([cur | acc]), <<>>}

  defp quoted(<<?", ?", rest::binary>>, acc, cur), do: quoted(rest, acc, cur <> ~s("))
  defp quoted(<<?", rest::binary>>, acc, cur), do: field(rest, acc, cur)
  defp quoted(<<c, rest::binary>>, acc, cur), do: quoted(rest, acc, cur <> <<c>>)
  defp quoted(<<>>, acc, cur), do: {Enum.reverse([cur | acc]), <<>>}
end
