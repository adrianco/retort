defmodule BrazilianSoccer.Dates do
  @moduledoc """
  Parses the date formats found in the datasets and in user queries:

    * ISO date, optionally followed by a time: `"2023-09-24"`, `"2012-05-19 18:30:00"`
    * Brazilian date: `"29/03/2003"`
  """

  @doc """
  Parses a date string into a `Date`.

      iex> BrazilianSoccer.Dates.parse("29/03/2003")
      {:ok, ~D[2003-03-29]}
      iex> BrazilianSoccer.Dates.parse("2012-05-19 18:30:00")
      {:ok, ~D[2012-05-19]}
      iex> BrazilianSoccer.Dates.parse("not a date")
      :error
  """
  @spec parse(binary()) :: {:ok, Date.t()} | :error
  def parse(text) when is_binary(text) do
    text = String.trim(text)

    case Regex.run(~r/^(\d{4})-(\d{1,2})-(\d{1,2})/, text) do
      [_, y, m, d] ->
        to_date(y, m, d)

      nil ->
        case Regex.run(~r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text) do
          [_, d, m, y] -> to_date(y, m, d)
          nil -> :error
        end
    end
  end

  def parse(_), do: :error

  defp to_date(y, m, d) do
    case Date.new(String.to_integer(y), String.to_integer(m), String.to_integer(d)) do
      {:ok, date} -> {:ok, date}
      {:error, _} -> :error
    end
  end
end
