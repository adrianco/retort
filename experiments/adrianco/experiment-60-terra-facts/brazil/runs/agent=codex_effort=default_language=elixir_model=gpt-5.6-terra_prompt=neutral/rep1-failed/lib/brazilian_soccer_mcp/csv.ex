defmodule BrazilianSoccerMcp.CSV do
  @moduledoc "A small RFC-4180 compatible CSV reader used to avoid a runtime dependency."

  @spec read(Path.t()) :: {:ok, [map()]} | {:error, term()}
  def read(path) do
    with {:ok, contents} <- File.read(path),
         [header | rows] <- parse(contents) do
      keys = Enum.map(header, &String.trim_leading(&1, "\uFEFF"))
      {:ok, Enum.map(rows, &Map.new(Enum.zip(keys, &1)))}
    else
      [] -> {:ok, []}
      error -> error
    end
  end

  @spec parse(binary()) :: [[String.t()]]
  def parse(contents), do: parse_chars(String.to_charlist(contents), [], [], [], false)

  defp parse_chars([], field, row, rows, _quoted), do: finish(rows, row, field)

  defp parse_chars([?", ?" | rest], field, row, rows, true),
    do: parse_chars(rest, [?"] ++ field, row, rows, true)

  defp parse_chars([?" | rest], field, row, rows, quoted),
    do: parse_chars(rest, field, row, rows, not quoted)

  defp parse_chars([?, | rest], field, row, rows, false),
    do: parse_chars(rest, [], [field_to_string(field) | row], rows, false)

  defp parse_chars([?\r, ?\n | rest], field, row, rows, false),
    do: parse_chars(rest, [], [], finish_row(rows, row, field), false)

  defp parse_chars([?\n | rest], field, row, rows, false),
    do: parse_chars(rest, [], [], finish_row(rows, row, field), false)

  defp parse_chars([char | rest], field, row, rows, quoted),
    do: parse_chars(rest, [char | field], row, rows, quoted)

  defp finish(rows, [], []), do: Enum.reverse(rows)

  defp finish(rows, row, field),
    do: Enum.reverse([[field_to_string(field) | row] |> Enum.reverse() | rows])

  defp finish_row(rows, row, field), do: [[field_to_string(field) | row] |> Enum.reverse() | rows]
  defp field_to_string(chars), do: chars |> Enum.reverse() |> List.to_string()
end
