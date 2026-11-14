defmodule BrazilianSoccer.Text do
  @moduledoc "Text helpers: accent-insensitive normalisation and value parsing."

  @doc "Lower-cases, strips accents/cedillas and collapses whitespace."
  def normalize(nil), do: ""

  def normalize(s) when is_binary(s) do
    s
    |> String.normalize(:nfd)
    |> String.replace(~r/\p{Mn}/u, "")
    |> String.downcase()
    |> String.replace(~r/\s+/u, " ")
    |> String.trim()
  end

  @doc "Parses integers written as `3`, `3.0`; returns nil for `NA`, `-`, blanks."
  def to_int(nil), do: nil
  def to_int(n) when is_integer(n), do: n
  def to_int(n) when is_float(n), do: trunc(n)

  def to_int(s) when is_binary(s) do
    case Float.parse(String.trim(s)) do
      {f, ""} -> trunc(f)
      _ -> nil
    end
  end

  @doc """
  Parses the date formats found in the datasets: ISO (`2023-09-24`), ISO with
  time (`2012-05-19 18:30:00`) and Brazilian (`29/03/2003`).
  Returns `{date, time_string | nil}` or `nil`.
  """
  def parse_datetime(nil), do: nil

  def parse_datetime(s) when is_binary(s) do
    s = String.trim(s)

    cond do
      m = Regex.run(~r/^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ](\d{1,2}:\d{2})(?::\d{2})?)?/, s) ->
        [_, y, mo, d | rest] = m
        build_date(y, mo, d, List.first(rest))

      m = Regex.run(~r/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}:\d{2}))?/, s) ->
        [_, d, mo, y | rest] = m
        build_date(y, mo, d, List.first(rest))

      true ->
        nil
    end
  end

  def parse_date(s) do
    case parse_datetime(s) do
      {date, _} -> date
      nil -> nil
    end
  end

  defp build_date(y, mo, d, time) do
    case Date.new(String.to_integer(y), String.to_integer(mo), String.to_integer(d)) do
      {:ok, date} -> {date, time}
      _ -> nil
    end
  end
end
