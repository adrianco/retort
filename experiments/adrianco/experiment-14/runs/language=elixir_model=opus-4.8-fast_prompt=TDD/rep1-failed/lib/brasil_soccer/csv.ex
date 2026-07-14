defmodule BrasilSoccer.CSV do
  @moduledoc """
  A minimal, dependency-free CSV parser tailored to the Kaggle datasets used by
  this project.

  It supports the subset of RFC 4180 that the data needs: quoted fields,
  embedded commas and newlines inside quotes, doubled `""` escapes, CRLF or LF
  line endings, a leading UTF-8 byte-order mark, and ragged rows (missing
  trailing columns are padded with empty strings). All values are returned as
  strings keyed by the header row.
  """

  @bom "﻿"

  @doc """
  Parse CSV `content` into a list of maps keyed by the header row.
  """
  @spec parse(binary()) :: [map()]
  def parse(content) when is_binary(content) do
    content
    |> strip_bom()
    |> tokenize()
    |> rows_to_maps()
  end

  @doc "Read a file from disk and parse it with `parse/1`."
  @spec parse_file(Path.t()) :: [map()]
  def parse_file(path) do
    path |> File.read!() |> parse()
  end

  defp strip_bom(@bom <> rest), do: rest
  defp strip_bom(content), do: content

  # Split into a list of rows, each a list of field strings, honouring quotes.
  defp tokenize(content) do
    {rows, field, row, _state} =
      content
      |> String.to_charlist()
      |> Enum.reduce({[], [], [], false}, &consume/2)

    # Flush any final pending field/row (a file may not end with a newline).
    rows =
      if field == [] and row == [] do
        rows
      else
        [Enum.reverse([flush(field) | row]) | rows]
      end

    rows
    |> Enum.reverse()
    |> Enum.reject(&blank_row?/1)
  end

  # A blank line tokenizes to a single empty field; drop those.
  defp blank_row?([""]), do: true
  defp blank_row?(_), do: false

  # inside a quoted field
  defp consume(?", {rows, field, row, true}), do: {rows, [?" | field], row, :maybe_close}
  defp consume(char, {rows, field, row, true}), do: {rows, [char | field], row, true}

  # just saw a closing quote: a second quote is an escaped literal quote
  defp consume(?", {rows, field, row, :maybe_close}),
    do: {rows, [?" | field], row, true}

  defp consume(?,, {rows, field, row, :maybe_close}),
    do: {rows, [], [flush(field) | row], false}

  defp consume(?\n, {rows, field, row, :maybe_close}),
    do: {[Enum.reverse([flush(field) | row]) | rows], [], [], false}

  defp consume(?\r, {rows, field, row, :maybe_close}), do: {rows, field, row, :maybe_close}
  defp consume(_char, {rows, field, row, :maybe_close}), do: {rows, field, row, :maybe_close}

  # normal (unquoted) state
  defp consume(?", {rows, [], row, false}), do: {rows, [?" | []], row, true}
  defp consume(?", {rows, field, row, false}), do: {rows, [?" | field], row, true}
  defp consume(?,, {rows, field, row, false}), do: {rows, [], [flush(field) | row], false}

  defp consume(?\n, {rows, field, row, false}),
    do: {[Enum.reverse([flush(field) | row]) | rows], [], [], false}

  defp consume(?\r, {rows, field, row, false}), do: {rows, field, row, false}
  defp consume(char, {rows, field, row, false}), do: {rows, [char | field], row, false}

  # Turn an accumulated reversed charlist field into a trimmed string, removing
  # surrounding quotes that wrapped the whole field.
  defp flush(field) do
    field
    |> Enum.reverse()
    |> List.to_string()
    |> unquote_field()
  end

  defp unquote_field(<<?", rest::binary>>) do
    rest
    |> String.replace_suffix(~s("), "")
    |> String.replace(~s(""), ~s("))
  end

  defp unquote_field(value), do: value

  defp rows_to_maps([]), do: []

  defp rows_to_maps([header | rows]) do
    width = length(header)

    Enum.map(rows, fn row ->
      row = pad(row, width)

      header
      |> Enum.zip(row)
      |> Map.new()
    end)
  end

  defp pad(row, width) do
    case width - length(row) do
      n when n > 0 -> row ++ List.duplicate("", n)
      _ -> Enum.take(row, width)
    end
  end
end
