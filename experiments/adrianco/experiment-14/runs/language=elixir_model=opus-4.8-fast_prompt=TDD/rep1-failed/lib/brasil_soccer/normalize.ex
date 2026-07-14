defmodule BrasilSoccer.Normalize do
  @moduledoc """
  Team-name normalisation.

  The datasets refer to the same club in several ways — with a Brazilian state
  suffix (`"Palmeiras-SP"`), a country code (`"Nacional (URU)"`), spaced
  hyphens (`"América - MG"`), or plain (`"Palmeiras"`). This module produces a
  clean display name and a comparison key so those variants collapse together.
  """

  # Brazilian state abbreviations plus a handful of CONMEBOL country codes that
  # appear as suffixes in the Libertadores data.
  @suffix_codes ~w(
    AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO
    ARG URU PAR CHI BOL PER ECU EQU COL VEN BRA PAR MEX USA
  )

  @doc """
  Return a cleaned-up display name: trimmed and with any trailing state or
  country code removed.
  """
  @spec team_name(String.t()) :: String.t()
  def team_name(name) when is_binary(name) do
    name
    |> String.trim()
    |> strip_paren_code()
    |> strip_hyphen_code()
    |> String.trim()
  end

  @doc """
  Return a comparison key: the display name lower-cased, with accents removed
  and internal whitespace collapsed.
  """
  @spec key(String.t()) :: String.t()
  def key(name) when is_binary(name) do
    name
    |> team_name()
    |> deaccent()
    |> String.downcase()
    |> String.replace(~r/\s+/u, " ")
    |> String.trim()
  end

  @doc """
  True when `a` and `b` refer to the same (or a containing) team after
  normalisation. Containment makes `"São Paulo FC"` match a `"sao paulo"`
  query.
  """
  @spec matches?(String.t(), String.t()) :: boolean()
  def matches?(a, b) do
    ka = key(a)
    kb = key(b)
    ka != "" and kb != "" and (String.contains?(ka, kb) or String.contains?(kb, ka))
  end

  # " (URU)" / "(EQU)" at the end of the string
  defp strip_paren_code(name) do
    case Regex.run(~r/^(.*?)\s*\(([A-Za-z]{2,3})\)$/u, name) do
      [_, base, code] -> if upcase_known?(code), do: String.trim(base), else: name
      _ -> name
    end
  end

  # "-SP" or " - MG" at the end of the string
  defp strip_hyphen_code(name) do
    case Regex.run(~r/^(.*?)\s*-\s*([A-Za-z]{2,3})$/u, name) do
      [_, base, code] -> if upcase_known?(code), do: String.trim(base), else: name
      _ -> name
    end
  end

  defp upcase_known?(code), do: String.upcase(code) in @suffix_codes

  defp deaccent(string) do
    string
    |> :unicode.characters_to_nfd_binary()
    |> String.replace(~r/[\x{0300}-\x{036f}]/u, "")
  end
end
