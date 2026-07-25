defmodule BrazilianSoccer.Query.Stats do
  @moduledoc """
  Aggregate statistics across the match graph: goals per match, home
  advantage, biggest wins, season-by-season trends and season comparisons.
  """

  alias BrazilianSoccer.Data.Graph
  alias BrazilianSoccer.Model.Match
  alias BrazilianSoccer.Query.{Filters, Matches}

  @doc """
  Headline numbers for a slice of the data.

  Arguments: optional `competition`, `season`, `season_from`, `season_to`,
  `team`.
  """
  @spec overview(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def overview(graph, args \\ %{}) do
    with {:ok, result} <- Matches.search(graph, Map.put(to_map(args), :limit, :all)) do
      matches = Enum.filter(result.matches, &Match.played?/1)

      case matches do
        [] ->
          {:error, {:no_matches, result.filters}}

        _ ->
          by_season =
            matches
            |> Enum.group_by(& &1.season)
            |> Enum.sort_by(fn {season, _} -> season || 0 end)
            |> Enum.map(fn {season, list} -> {season, season_block(list)} end)

          {:ok,
           Map.merge(season_block(matches), %{
             filters: result.filters,
             by_season: by_season,
             by_competition:
               matches
               |> Enum.group_by(& &1.competition)
               |> Enum.map(fn {competition, list} -> {competition, season_block(list)} end)
               |> Enum.sort_by(fn {_, block} -> -block.matches end),
             highest_scoring: Enum.max_by(matches, &Match.total_goals/1, fn -> nil end),
             biggest_margin: Enum.max_by(matches, &Match.margin/1, fn -> nil end)
           })}
      end
    end
  end

  @doc """
  Biggest wins (by goal margin).

  Arguments: optional `team`, `competition`, `season`, `venue`, `limit`.
  """
  @spec biggest_wins(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def biggest_wins(graph, args \\ %{}) do
    limit = Filters.limit(Filters.get(args, :limit), 10)

    with {:ok, team} <- Filters.team(graph, Filters.get(args, :team)),
         {:ok, result} <- Matches.search(graph, Map.put(to_map(args), :limit, :all)) do
      matches =
        result.matches
        |> Enum.filter(&Match.played?/1)
        |> then(fn list ->
          if team, do: Enum.filter(list, &(Match.outcome_for(&1, team.id) == :win)), else: list
        end)
        |> Enum.filter(&(Match.margin(&1) > 0))
        |> Enum.sort_by(&{-Match.margin(&1), -Match.total_goals(&1)})
        |> Enum.take(limit)

      {:ok, %{matches: matches, team: team, filters: result.filters}}
    end
  end

  @doc """
  Highest scoring matches.

  Arguments: optional `team`, `competition`, `season`, `limit`.
  """
  @spec highest_scoring(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def highest_scoring(graph, args \\ %{}) do
    limit = Filters.limit(Filters.get(args, :limit), 10)

    with {:ok, result} <- Matches.search(graph, Map.put(to_map(args), :limit, :all)) do
      matches =
        result.matches
        |> Enum.filter(&Match.played?/1)
        |> Enum.sort_by(&{-Match.total_goals(&1), -Match.margin(&1)})
        |> Enum.take(limit)

      {:ok, %{matches: matches, filters: result.filters}}
    end
  end

  @doc """
  Compare seasons of a competition side by side.

  Arguments: `seasons` (list, required), optional `competition` (default
  Série A).
  """
  @spec compare_seasons(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def compare_seasons(graph, args) do
    with {:ok, competition} <- competition(args),
         {:ok, seasons} <- Filters.seasons(Filters.get(args, :seasons)) do
      seasons =
        case seasons do
          [] -> []
          list -> Enum.sort(list)
        end

      if seasons == [] do
        {:error, {:missing_argument, :seasons}}
      else
        blocks =
          Enum.map(seasons, fn season ->
            matches =
              graph
              |> Graph.matches_for_competition(competition, season)
              |> Enum.filter(&Match.played?/1)

            champion =
              case BrazilianSoccer.Query.Competitions.champion(graph, %{
                     competition: competition,
                     season: season
                   }) do
                {:ok, %{champion: champion}} -> champion
                {:error, _} -> nil
              end

            %{
              season: season,
              available: matches != [],
              stats: season_block(matches),
              champion: champion,
              top_scoring_team: top_scoring_team(graph, matches)
            }
          end)

        {:ok, %{competition: Graph.competition(competition), seasons: blocks}}
      end
    end
  end

  @doc """
  Home advantage broken down per season.

  Arguments: optional `competition` (default Série A).
  """
  @spec home_advantage(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def home_advantage(graph, args \\ %{}) do
    with {:ok, competition} <- competition(args) do
      matches =
        graph
        |> Graph.matches_for_competition(competition)
        |> Enum.filter(&Match.played?/1)

      by_season =
        matches
        |> Enum.group_by(& &1.season)
        |> Enum.sort_by(fn {season, _} -> season || 0 end)
        |> Enum.map(fn {season, list} -> {season, season_block(list)} end)

      {:ok,
       %{
         competition: Graph.competition(competition),
         overall: season_block(matches),
         by_season: by_season
       }}
    end
  end

  # --- helpers -------------------------------------------------------------

  @doc "Goals / results summary for a list of played matches."
  @spec season_block([Match.t()]) :: map
  def season_block([]) do
    %{
      matches: 0,
      goals: 0,
      goals_per_match: 0.0,
      home_wins: 0,
      away_wins: 0,
      draws: 0,
      home_win_rate: 0.0,
      away_win_rate: 0.0,
      draw_rate: 0.0,
      home_goals: 0,
      away_goals: 0,
      clean_sheets: 0,
      both_scored_rate: 0.0
    }
  end

  def season_block(matches) do
    total = length(matches)
    home_wins = Enum.count(matches, &(Match.result(&1) == :home_win))
    away_wins = Enum.count(matches, &(Match.result(&1) == :away_win))
    draws = Enum.count(matches, &(Match.result(&1) == :draw))
    home_goals = Enum.sum(Enum.map(matches, & &1.home_goals))
    away_goals = Enum.sum(Enum.map(matches, & &1.away_goals))

    %{
      matches: total,
      goals: home_goals + away_goals,
      goals_per_match: Float.round((home_goals + away_goals) / total, 2),
      home_wins: home_wins,
      away_wins: away_wins,
      draws: draws,
      home_win_rate: percentage(home_wins, total),
      away_win_rate: percentage(away_wins, total),
      draw_rate: percentage(draws, total),
      home_goals: home_goals,
      away_goals: away_goals,
      clean_sheets: Enum.count(matches, &(&1.home_goals == 0 or &1.away_goals == 0)),
      both_scored_rate:
        percentage(Enum.count(matches, &(&1.home_goals > 0 and &1.away_goals > 0)), total)
    }
  end

  defp top_scoring_team(_graph, []), do: nil

  defp top_scoring_team(graph, matches) do
    matches
    |> Enum.flat_map(fn match ->
      [{match.home_id, match.home_goals}, {match.away_id, match.away_goals}]
    end)
    |> Enum.reduce(%{}, fn {team_id, goals}, acc ->
      Map.update(acc, team_id, goals, &(&1 + goals))
    end)
    |> Enum.max_by(fn {_, goals} -> goals end, fn -> nil end)
    |> case do
      nil -> nil
      {team_id, goals} -> %{team: Graph.team(graph, team_id), goals: goals}
    end
  end

  defp competition(args) do
    case Filters.get(args, :competition) do
      nil -> {:ok, :serie_a}
      value -> Filters.competition(value)
    end
  end

  defp percentage(_part, 0), do: 0.0
  defp percentage(part, total), do: Float.round(part * 100 / total, 1)

  defp to_map(args), do: Filters.atomize(args)
end
