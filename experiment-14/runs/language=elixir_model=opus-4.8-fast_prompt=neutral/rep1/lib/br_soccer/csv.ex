defmodule BrSoccer.CSV do
  @moduledoc """
  Minimal, dependency-free RFC 4180 CSV parser.

  Handles quoted fields, embedded commas/newlines/quotes (escaped as `""`),
  CRLF/LF line endings and a leading UTF-8 BOM. The datasets are small enough
  (the largest is ~9 MB) that reading them fully into memory is fine.
  """

  @doc """
  Parse a CSV file at `path` into a list of maps keyed by the header row.

  The header is taken from the first record. A leading UTF-8 BOM on the first
  header cell is stripped so columns line up regardless of how the file was
  exported.
  """
  @spec parse_file(Path.t()) :: [map()]
  def parse_file(path) do
    path
    |> File.read!()
    |> parse_string()
  end

  @doc "Parse a CSV string into a list of header-keyed maps."
  @spec parse_string(binary()) :: [map()]
  def parse_string(content) do
    case parse_rows(content) do
      [] ->
        []

      [header | rows] ->
        keys = Enum.map(header, &strip_bom/1)

        Enum.map(rows, fn row ->
          keys
          |> Enum.zip(pad(row, length(keys)))
          |> Map.new()
        end)
    end
  end

  @doc "Parse a CSV string into a list of rows, each a list of string cells."
  @spec parse_rows(binary()) :: [[binary()]]
  def parse_rows(content) do
    content
    |> scan([], [], "", false)
    |> Enum.reverse()
    |> Enum.reject(&blank_row?/1)
  end

  # State machine: (input, rows_acc, current_row, current_field, in_quotes?)
  defp scan(<<>>, rows, row, field, _in_quotes) do
    [Enum.reverse([field | row]) | rows]
  end

  # Escaped quote inside a quoted field ("")
  defp scan(<<?", ?", rest::binary>>, rows, row, field, true) do
    scan(rest, rows, row, field <> "\"", true)
  end

  # Toggle quoting
  defp scan(<<?", rest::binary>>, rows, row, field, in_quotes) do
    scan(rest, rows, row, field, not in_quotes)
  end

  # Field separator (only when not inside quotes)
  defp scan(<<?,, rest::binary>>, rows, row, field, false) do
    scan(rest, rows, [field | row], "", false)
  end

  # Row separators (CRLF / LF / CR) when not inside quotes
  defp scan(<<?\r, ?\n, rest::binary>>, rows, row, field, false) do
    scan(rest, [Enum.reverse([field | row]) | rows], [], "", false)
  end

  defp scan(<<?\n, rest::binary>>, rows, row, field, false) do
    scan(rest, [Enum.reverse([field | row]) | rows], [], "", false)
  end

  defp scan(<<?\r, rest::binary>>, rows, row, field, false) do
    scan(rest, [Enum.reverse([field | row]) | rows], [], "", false)
  end

  # Any other byte (including newlines inside quotes) is part of the field.
  defp scan(<<c::utf8, rest::binary>>, rows, row, field, in_quotes) do
    scan(rest, rows, row, field <> <<c::utf8>>, in_quotes)
  end

  defp scan(<<c, rest::binary>>, rows, row, field, in_quotes) do
    scan(rest, rows, row, field <> <<c>>, in_quotes)
  end

  defp blank_row?([""]), do: true
  defp blank_row?([]), do: true
  defp blank_row?(_), do: false

  defp pad(row, n) do
    case length(row) do
      len when len >= n -> Enum.take(row, n)
      len -> row ++ List.duplicate("", n - len)
    end
  end

  defp strip_bom(<<0xEF, 0xBB, 0xBF, rest::binary>>), do: rest
  defp strip_bom(other), do: other
end
