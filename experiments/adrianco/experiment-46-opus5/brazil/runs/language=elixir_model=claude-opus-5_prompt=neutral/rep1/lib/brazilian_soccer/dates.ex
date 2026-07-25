defmodule BrazilianSoccer.Dates do
  @moduledoc """
  Tolerant date parsing for the mixed formats found in the datasets:

    * ISO            `"2023-09-24"`
    * ISO + time     `"2012-05-19 18:30:00"`
    * Brazilian      `"29/03/2003"`
    * junk           `"NA"`, `""`, `"-"`
  """

  @doc """
  Parse a date cell into `{date, time}` where either element may be `nil`.
  """
  @spec parse(binary | nil) :: {Date.t() | nil, Time.t() | nil}
  def parse(nil), do: {nil, nil}

  def parse(value) when is_binary(value) do
    value = value |> String.trim() |> String.trim("\"") |> String.trim()

    case value do
      "" -> {nil, nil}
      "NA" -> {nil, nil}
      "-" -> {nil, nil}
      _ -> do_parse(value)
    end
  end

  def parse(_), do: {nil, nil}

  defp do_parse(value) do
    {date_part, time_part} =
      case String.split(value, ~r/[ T]/, parts: 2) do
        [d] -> {d, nil}
        [d, t] -> {d, t}
      end

    {parse_date(date_part), parse_time(time_part)}
  end

  defp parse_date(<<y::binary-4, "-", m::binary-2, "-", d::binary-2>>) do
    build(y, m, d)
  end

  defp parse_date(str) do
    case String.split(str, ~r/[\/.]/) do
      [d, m, y] when byte_size(y) == 4 -> build(y, m, d)
      [y, m, d] when byte_size(y) == 4 -> build(y, m, d)
      _ -> nil
    end
  end

  defp build(y, m, d) do
    with {year, _} <- Integer.parse(y),
         {month, _} <- Integer.parse(m),
         {day, _} <- Integer.parse(d),
         {:ok, date} <- Date.new(year, month, day) do
      date
    else
      _ -> nil
    end
  end

  @doc "Parse a `HH:MM(:SS)` cell."
  @spec parse_time(binary | nil) :: Time.t() | nil
  def parse_time(nil), do: nil

  def parse_time(str) when is_binary(str) do
    case String.split(String.trim(str), ":") do
      [h, m | rest] ->
        sec = List.first(rest) || "0"

        with {hour, _} <- Integer.parse(h),
             {minute, _} <- Integer.parse(m),
             {second, _} <- Integer.parse(sec),
             {:ok, time} <- Time.new(hour, minute, second) do
          time
        else
          _ -> nil
        end

      _ ->
        nil
    end
  end

  @doc "Accept a `Date`, an ISO/BR string or `nil` and return a `Date` or `nil`."
  @spec to_date(Date.t() | binary | nil) :: Date.t() | nil
  def to_date(%Date{} = date), do: date

  def to_date(value) when is_binary(value) do
    {date, _} = parse(value)
    date
  end

  def to_date(_), do: nil

  @doc "Format a date the way the answers show it (`2023-09-03`, or `?` when unknown)."
  @spec format(Date.t() | nil) :: binary
  def format(%Date{} = date), do: Date.to_iso8601(date)
  def format(nil), do: "date unknown"
end
