defmodule BrazilianSoccer.TeamName do
  @moduledoc """
  Normalization helpers for Brazilian soccer team names.

  The datasets use several naming conventions for the same club, e.g.
  `"Palmeiras-SP"`, `"Palmeiras"`, `"América - MG"`, `"Nacional (URU)"` and
  accented vs. unaccented spellings (`"São Paulo"` vs `"Sao Paulo"`). These
  helpers produce a clean display name and an accent/case-insensitive matching
  key so the same club is recognized regardless of source file.
  """

  # A trailing state/country code: "-SP", " - MG", " (URU)", "-EQU".
  @suffix ~r/\s*[-(]\s*[A-Z]{2,3}\)?\s*$/

  @doc """
  Return a human-readable team name with any trailing state/country suffix and
  surrounding whitespace removed.
  """
  @spec clean(binary()) :: binary()
  def clean(name) when is_binary(name) do
    name
    |> String.trim()
    |> String.replace(@suffix, "")
    |> String.trim()
  end

  @doc """
  Return a canonical identity key: accent-stripped, lowercased, whitespace
  collapsed, but with any state/country suffix *preserved*. This keeps distinct
  clubs that differ only by suffix apart (e.g. `Atlético-MG` vs `Atlético-PR`),
  which matters for computing standings.
  """
  @spec key(binary()) :: binary()
  def key(name) when is_binary(name) do
    name
    |> normalize()
  end

  @doc """
  Return a fuzzy matching key: like `key/1` but with the state/country suffix
  removed. Use this to match user-supplied team names (`"Flamengo"` finds
  `"Flamengo-RJ"`).
  """
  @spec base(binary()) :: binary()
  def base(name) when is_binary(name) do
    name
    |> clean()
    |> normalize()
  end

  @doc """
  Return true when two team names refer to the same club, ignoring suffixes,
  accents and case.
  """
  @spec matches?(binary(), binary()) :: boolean()
  def matches?(a, b) when is_binary(a) and is_binary(b), do: base(a) == base(b)

  defp normalize(name) do
    name
    |> String.trim()
    |> strip_accents()
    |> String.downcase()
    |> String.replace(~r/\s+/u, " ")
    |> String.trim()
  end

  defp strip_accents(string) do
    string
    |> String.normalize(:nfd)
    |> String.replace(~r/[\x{0300}-\x{036f}]/u, "")
  end
end
