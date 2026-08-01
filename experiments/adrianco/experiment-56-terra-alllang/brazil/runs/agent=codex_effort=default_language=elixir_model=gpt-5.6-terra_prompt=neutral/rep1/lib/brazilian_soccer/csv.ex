defmodule BrazilianSoccer.CSV do
  @moduledoc false
  # RFC 4180-style CSV parser; quoted commas, escaped quotes and UTF-8 are supported.
  def read(path) do
    [header | rows] =
      path
      |> File.stream!(:line, [])
      |> Enum.map(&String.trim_trailing(&1, "\n\r"))
      |> Enum.reject(&(&1 == ""))

    headers = parse_line(header) |> Enum.map(&String.trim_leading(&1, "\uFEFF"))
    Enum.map(rows, fn line -> Map.new(Enum.zip(headers, parse_line(line))) end)
  end

  def parse_line(line), do: parse(line, [], "", false)
  defp parse(<<>>, fields, field, _quoted), do: Enum.reverse([field | fields])

  defp parse(<<"\"\"", rest::binary>>, fields, field, true),
    do: parse(rest, fields, field <> "\"", true)

  defp parse(<<"\"", rest::binary>>, fields, field, quoted),
    do: parse(rest, fields, field, not quoted)

  defp parse(<<",", rest::binary>>, fields, field, false),
    do: parse(rest, [field | fields], "", false)

  defp parse(<<char::utf8, rest::binary>>, fields, field, quoted),
    do: parse(rest, fields, field <> <<char::utf8>>, quoted)
end
