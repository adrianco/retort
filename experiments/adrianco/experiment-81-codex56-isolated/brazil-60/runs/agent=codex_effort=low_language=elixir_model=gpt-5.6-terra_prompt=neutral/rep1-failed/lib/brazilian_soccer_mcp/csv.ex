defmodule BrazilianSoccerMcp.CSV do
  @moduledoc false
  # RFC-4180 enough for the supplied files, including commas and escaped quotes.
  def read(path) do
    [header | rows] = path |> File.read!() |> String.replace_prefix("\uFEFF", "") |> records()
    keys = parse_line(header)
    Enum.map(rows, fn row -> Map.new(Enum.zip(keys, parse_line(row))) end)
  end

  defp records(text) do
    {out, current, _quoted} =
      text
      |> String.graphemes()
      |> Enum.reduce({[], "", false}, fn
        "\"", {acc, cur, q} -> {acc, cur <> "\"", not q}
        "\n", {acc, cur, false} -> {[cur | acc], "", false}
        char, {acc, cur, q} -> {acc, cur <> char, q}
      end)

    Enum.reverse(if String.trim(current) == "", do: out, else: [current | out])
  end

  defp parse_line(line) do
    {values, field, _quoted} =
      line
      |> String.graphemes()
      |> Enum.reduce({[], "", false}, fn
        "\"", {acc, cur, false} -> {acc, cur, true}
        "\"", {acc, cur, true} -> {acc, cur, false}
        ",", {acc, cur, false} -> {[cur | acc], "", false}
        char, {acc, cur, q} -> {acc, cur <> char, q}
      end)

    Enum.reverse([field | values]) |> Enum.map(&String.replace(&1, "\"\"", "\""))
  end
end
