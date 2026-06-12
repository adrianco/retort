defmodule BrazilianSoccer.CSV do
  @moduledoc """
  A small, dependency-free RFC 4180 CSV parser.

  It supports quoted fields, escaped double quotes (`""`), commas and newlines
  embedded inside quoted fields, both `\\n` and `\\r\\n` line endings, and a
  leading UTF-8 BOM. This is sufficient for the Kaggle datasets shipped with
  this project (notably the FIFA file which contains quoted dates such as
  `"Jul 1, 2004"`).
  """

  @bom "﻿"

  @doc """
  Parse CSV `content` into a list of rows, where each row is a list of string
  fields. A single trailing newline is ignored.
  """
  @spec parse(binary()) :: [[binary()]]
  def parse(content) when is_binary(content) do
    content
    |> strip_bom()
    |> do_parse([], [], "", false)
  end

  @doc """
  Parse CSV `content` using the first row as the header. Returns a list of maps
  keyed by the header field names.
  """
  @spec parse_to_maps(binary()) :: [map()]
  def parse_to_maps(content) when is_binary(content) do
    case parse(content) do
      [] -> []
      [headers | rows] -> Enum.map(rows, &row_to_map(headers, &1))
    end
  end

  defp row_to_map(headers, row) do
    headers
    |> Enum.zip(pad(row, length(headers)))
    |> Map.new()
  end

  defp pad(row, n) when length(row) >= n, do: Enum.take(row, n)
  defp pad(row, n), do: row ++ List.duplicate("", n - length(row))

  defp strip_bom(@bom <> rest), do: rest
  defp strip_bom(content), do: content

  # State machine: accumulate the current field, the current row, and all rows.
  # `quoted?` tracks whether we are inside a quoted field.

  # End of input.
  defp do_parse("", rows, row, field, _quoted?) do
    finalize(rows, row, field)
  end

  # Inside a quoted field.
  defp do_parse(<<?", ?", rest::binary>>, rows, row, field, true) do
    do_parse(rest, rows, row, field <> "\"", true)
  end

  defp do_parse(<<?", rest::binary>>, rows, row, field, true) do
    do_parse(rest, rows, row, field, false)
  end

  defp do_parse(<<char::utf8, rest::binary>>, rows, row, field, true) do
    do_parse(rest, rows, row, field <> <<char::utf8>>, true)
  end

  # Outside a quoted field.
  defp do_parse(<<?", rest::binary>>, rows, row, field, false) do
    do_parse(rest, rows, row, field, true)
  end

  defp do_parse(<<?,, rest::binary>>, rows, row, field, false) do
    do_parse(rest, rows, [field | row], "", false)
  end

  defp do_parse(<<?\r, ?\n, rest::binary>>, rows, row, field, false) do
    do_parse(rest, [Enum.reverse([field | row]) | rows], [], "", false)
  end

  defp do_parse(<<?\n, rest::binary>>, rows, row, field, false) do
    do_parse(rest, [Enum.reverse([field | row]) | rows], [], "", false)
  end

  defp do_parse(<<char::utf8, rest::binary>>, rows, row, field, false) do
    do_parse(rest, rows, row, field <> <<char::utf8>>, false)
  end

  # Emit the final (possibly empty) row, dropping a single trailing blank line.
  defp finalize(rows, [], "") do
    Enum.reverse(rows)
  end

  defp finalize(rows, row, field) do
    Enum.reverse([Enum.reverse([field | row]) | rows])
  end
end
