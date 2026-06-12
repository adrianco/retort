defmodule BrSoccer.Competitions do
  @moduledoc """
  League tables and competition-level views computed from match results.

  Several files overlap (the Brasileirão appears in `Brasileirao_Matches.csv`,
  `novo_campeonato_brasileiro.csv` and the Serie A rows of
  `BR-Football-Dataset.csv`). To avoid double-counting, standings are computed
  from a single preferred source per season.
  """

  alias BrSoccer.{Match, Matches, Repo}

  # Preferred source order when more than one covers the same season.
  @source_priority [:brasileirao_csv, :novo, :br_football, :cup_csv, :libertadores_csv]

  @doc """
  League standings for a competition and season.

  Returns an ordered list of record maps (see `BrSoccer.Teams.record/2` shape)
  each augmented with `:position`. Points = 3·W + D; ties broken by wins then
  goal difference then goals for.
  """
  def standings(competition, season) do
    competition
    |> season_matches(season)
    |> build_table()
  end

  @doc "The single source actually used for a competition/season's standings."
  def chosen_source(competition, season) do
    competition
    |> candidate_sources(season)
    |> List.first()
  end

  defp season_matches(competition, season) do
    source = chosen_source(competition, season)

    if source do
      Matches.search(
        competition: competition,
        season: season,
        source: source,
        scored_only: true
      )
    else
      []
    end
  end

  defp candidate_sources(competition, season) do
    present =
      Repo.matches()
      |> Enum.filter(&(&1.competition == competition and &1.season == season and Match.scored?(&1)))
      |> Enum.map(& &1.source)
      |> Enum.uniq()

    Enum.filter(@source_priority, &(&1 in present))
  end

  defp build_table(matches) do
    matches
    |> Enum.reduce(%{}, fn m, acc ->
      acc
      |> update_team(m.home_key, m.home, m.home_goal, m.away_goal)
      |> update_team(m.away_key, m.away, m.away_goal, m.home_goal)
    end)
    |> Map.values()
    |> Enum.map(&finalize/1)
    |> Enum.sort_by(&{&1.points, &1.wins, &1.goal_diff, &1.goals_for}, :desc)
    |> Enum.with_index(1)
    |> Enum.map(fn {row, pos} -> Map.put(row, :position, pos) end)
  end

  defp update_team(acc, key, name, gf, ga) do
    row =
      Map.get(acc, key, %{
        key: key,
        team: name,
        matches: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goals_for: 0,
        goals_against: 0
      })

    outcome =
      cond do
        gf > ga -> :wins
        gf < ga -> :losses
        true -> :draws
      end

    row =
      row
      |> Map.update!(:matches, &(&1 + 1))
      |> Map.update!(outcome, &(&1 + 1))
      |> Map.update!(:goals_for, &(&1 + gf))
      |> Map.update!(:goals_against, &(&1 + ga))

    Map.put(acc, key, row)
  end

  defp finalize(row) do
    row
    |> Map.put(:points, row.wins * 3 + row.draws)
    |> Map.put(:goal_diff, row.goals_for - row.goals_against)
    |> Map.put(:win_rate, if(row.matches == 0, do: 0.0, else: Float.round(row.wins * 100 / row.matches, 1)))
  end

  @doc "The champion (top of the table) for a competition/season, or nil."
  def champion(competition, season) do
    standings(competition, season) |> List.first()
  end

  @doc """
  Teams relegated in a Brasileirão season: the bottom `count` (default 4) of a
  20-team league. Returns `[]` when the table size doesn't look like a standard
  20-team season.
  """
  def relegated(season, count \\ 4) do
    table = standings(:brasileirao, season)

    if length(table) >= 16 do
      table |> Enum.take(-count)
    else
      []
    end
  end

  @doc "Seasons available for a competition (sorted)."
  def seasons(competition) do
    Repo.matches()
    |> Enum.filter(&(&1.competition == competition))
    |> Enum.map(& &1.season)
    |> Enum.reject(&is_nil/1)
    |> Enum.uniq()
    |> Enum.sort()
  end
end
