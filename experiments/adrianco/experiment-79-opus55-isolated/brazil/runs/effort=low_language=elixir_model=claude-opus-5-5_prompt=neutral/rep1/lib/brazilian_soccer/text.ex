defmodule BrazilianSoccer.Text do
  @moduledoc "Text helpers: accent folding, date and number parsing."

  @doc "Lower-cases and strips diacritics: \"São Paulo\" -> \"sao paulo\"."
  def fold(nil), do: ""

  def fold(s) when is_binary(s) do
    s
    |> String.normalize(:nfd)
    |> String.replace(~r/\p{Mn}/u, "")
    |> String.downcase()
    |> String.trim()
  end

  @doc """
  Parses the date formats found in the datasets: `2023-09-24`,
  `2012-05-19 18:30:00` and `29/03/2003`. Returns a `Date` or nil.
  """
  def parse_date(nil), do: nil
  def parse_date(%Date{} = d), do: d

  def parse_date(s) when is_binary(s) do
    s = String.trim(s)

    cond do
      m = Regex.run(~r/^(\d{4})-(\d{1,2})-(\d{1,2})/, s) -> build_date(m, [1, 2, 3])
      m = Regex.run(~r/^(\d{1,2})\/(\d{1,2})\/(\d{4})/, s) -> build_date(m, [3, 2, 1])
      true -> nil
    end
  end

  def parse_date(_), do: nil

  defp build_date(m, [yi, mi, di]) do
    [y, mo, d] = Enum.map([yi, mi, di], &String.to_integer(Enum.at(m, &1)))

    case Date.new(y, mo, d) do
      {:ok, date} -> date
      _ -> nil
    end
  end

  @doc "Parses \"2\", \"2.0\" -> 2; \"NA\", \"-\", \"\" -> nil."
  def parse_int(nil), do: nil
  def parse_int(n) when is_integer(n), do: n
  def parse_int(n) when is_float(n), do: round(n)

  def parse_int(s) when is_binary(s) do
    case Float.parse(String.trim(s)) do
      {f, ""} -> round(f)
      _ -> nil
    end
  end

  def blank?(nil), do: true
  def blank?(s) when is_binary(s), do: String.trim(s) == ""
  def blank?(_), do: false
end
