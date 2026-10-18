defmodule SoccerMcp.Parse do
  @moduledoc """
  Field parsers shared by the dataset loaders.

  Dates arrive as ISO (`2023-09-24`, `2012-05-19 18:30:00`), dotted
  (`2003.03.29`) or Brazilian (`29/03/2003`). Numbers arrive as integers, as
  floats such as `"1.0"`, or as empty strings for unplayed or unknown values.
  """

  @doc """
  Parses the date portion of a field. Returns `nil` when it cannot be read.

      iex> SoccerMcp.Parse.date("2012-05-19 18:30:00")
      ~D[2012-05-19]
      iex> SoccerMcp.Parse.date("29/03/2003")
      ~D[2003-03-29]
  """
  @spec date(String.t() | nil) :: Date.t() | nil
  def date(nil), do: nil

  def date(text) when is_binary(text) do
    text = String.trim(text)

    with nil <- iso_date(text),
         nil <- brazilian_date(text) do
      nil
    end
  end

  defp iso_date(text) do
    case Regex.run(~r/^(\d{4})[-.](\d{2})[-.](\d{2})/, text, capture: :all_but_first) do
      [y, m, d] -> to_date(y, m, d)
      nil -> nil
    end
  end

  defp brazilian_date(text) do
    case Regex.run(~r/^(\d{2})\/(\d{2})\/(\d{4})/, text, capture: :all_but_first) do
      [d, m, y] -> to_date(y, m, d)
      nil -> nil
    end
  end

  defp to_date(y, m, d) do
    case Date.new(String.to_integer(y), String.to_integer(m), String.to_integer(d)) do
      {:ok, date} -> date
      {:error, _} -> nil
    end
  end

  @doc """
  Parses an integer from a number-like field, accepting "2", "2.0" and "2.0 ".
  Returns `nil` for empty or non-numeric input.

      iex> SoccerMcp.Parse.int("1.0")
      1
      iex> SoccerMcp.Parse.int("")
      nil
  """
  @spec int(String.t() | nil) :: integer() | nil
  def int(nil), do: nil

  def int(text) when is_binary(text) do
    case Float.parse(String.trim(text)) do
      {value, _} -> trunc(value)
      :error -> nil
    end
  end

  @doc "Lowercase ASCII text with accents removed, for case-insensitive search."
  @spec fold(String.t()) :: String.t()
  def fold(text) do
    text
    |> :unicode.characters_to_nfd_binary()
    |> String.replace(~r/\p{Mn}/u, "")
    |> String.downcase()
    |> String.trim()
  end
end
