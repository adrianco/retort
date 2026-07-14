defmodule BrazilianSoccer.Queries.Source do
  @moduledoc """
  Cross-source de-duplication for aggregate queries.

  The same fixture frequently appears in more than one CSV file (e.g. a 2019
  Brasileirão match is present in `Brasileirao_Matches.csv`,
  `novo_campeonato_brasileiro.csv` and `BR-Football-Dataset.csv`), and the files
  use inconsistent team-name spellings that defeat row-level de-duplication.

  For correct standings, records and statistics we therefore pick a single
  authoritative source per `{competition, season}`: the source contributing the
  most matches for that pairing. Match *search* still spans every file; only
  aggregation uses this reduction.
  """

  alias BrazilianSoccer.Match

  @doc """
  Reduce matches to a single dominant source per `{competition, season}`.
  """
  @spec primary_per_season([Match.t()]) :: [Match.t()]
  def primary_per_season(matches) do
    matches
    |> Enum.group_by(fn %Match{competition: c, season: s} -> {c, s} end)
    |> Enum.flat_map(fn {_key, group} -> dominant_source(group) end)
  end

  defp dominant_source(group) do
    group
    |> Enum.group_by(& &1.source)
    |> Enum.max_by(fn {_source, matches} -> length(matches) end)
    |> elem(1)
  end
end
