defmodule BrazilianSoccer.Query.Teams do
  @moduledoc """
  Team records: win/draw/loss, goals, home vs away splits, form and profiles.
  """

  alias BrazilianSoccer.Data.Graph
  alias BrazilianSoccer.Model.Match
  alias BrazilianSoccer.Query.{Filters, Matches}

  @doc """
  Statistics for one team.

  Arguments: `team` (required), optional `season`, `season_from`, `season_to`,
  `competition`, `venue` (`home`/`away`/`all`), `date_from`, `date_to`.
  """
  @spec stats(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def stats(graph, args) do
    with {:ok, team} <- require_team(graph, Filters.get(args, :team)),
         {:ok, venue} <- Filters.venue(Filters.get(args, :venue)),
         {:ok, result} <-
           Matches.search(graph, Map.merge(to_map(args), %{team: team.id, limit: :all})) do
      matches = Enum.filter(result.matches, &Match.played?/1)

      {:ok,
       %{
         team: team,
         venue: venue,
         filters: result.filters,
         record: record(matches, team.id),
         home: record(Enum.filter(matches, &(&1.home_id == team.id)), team.id),
         away: record(Enum.filter(matches, &(&1.away_id == team.id)), team.id),
         by_competition: group_record(matches, team.id, & &1.competition),
         by_season: group_record(matches, team.id, & &1.season),
         form: matches |> Enum.take(5) |> Enum.map(&form_entry(&1, team.id)),
         biggest_win: biggest(matches, team.id, :win),
         biggest_loss: biggest(matches, team.id, :loss),
         matches: matches
       }}
    end
  end

  @doc """
  A team profile: identity, spellings found in the data, competitions,
  seasons, overall record and squad size from the FIFA dataset.
  """
  @spec profile(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def profile(graph, args) do
    with {:ok, team} <- require_team(graph, Filters.get(args, :team)) do
      matches = Graph.matches_for_team(graph, team.id)
      played = Enum.filter(matches, &Match.played?/1)
      players = Graph.players_for_club(graph, team.id)

      {:ok,
       %{
         team: team,
         record: record(played, team.id),
         by_competition: group_record(played, team.id, & &1.competition),
         seasons: Enum.sort(team.seasons),
         first_match: List.last(matches),
         last_match: List.first(matches),
         players: Enum.sort_by(players, &(-(&1.overall || 0))),
         player_count: length(players)
       }}
    end
  end

  @doc """
  Compare two teams: both records plus the head-to-head.

  Arguments: `team_a`, `team_b`, optional `season`, `competition`.
  """
  @spec compare(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def compare(graph, args) do
    with {:ok, a} <- require_team(graph, Filters.get(args, :team_a)),
         {:ok, b} <- require_team(graph, Filters.get(args, :team_b)),
         {:ok, stats_a} <- stats(graph, Map.merge(to_map(args), %{team: a.id})),
         {:ok, stats_b} <- stats(graph, Map.merge(to_map(args), %{team: b.id})),
         {:ok, h2h} <-
           Matches.head_to_head(
             graph,
             Map.merge(to_map(args), %{team_a: a.id, team_b: b.id})
           ) do
      {:ok, %{team_a: stats_a, team_b: stats_b, head_to_head: h2h}}
    end
  end

  @doc """
  Rank teams by record.

  Arguments: `metric` (`overall`/`home`/`away`), optional `competition`,
  `season`, `min_matches`, `limit`, `sort_by` (`win_rate`/`points`/`wins`/
  `goals_for`/`goals_against`/`goal_difference`).
  """
  @spec rankings(Graph.t(), map) :: {:ok, map} | {:error, tuple}
  def rankings(graph, args \\ %{}) do
    with {:ok, venue} <- Filters.venue(Filters.get(args, :metric) || Filters.get(args, :venue)),
         {:ok, competition} <- Filters.competition(Filters.get(args, :competition)),
         {:ok, season} <- Filters.season(Filters.get(args, :season)) do
      limit = Filters.limit(Filters.get(args, :limit), 10)
      sort_by = sort_key(Filters.get(args, :sort_by))

      matches =
        cond do
          competition -> Graph.matches_for_competition(graph, competition, season)
          season -> Enum.filter(Graph.all_matches(graph), &(&1.season == season))
          true -> Graph.all_matches(graph)
        end
        |> Enum.filter(&Match.played?/1)

      min_matches =
        Filters.integer(Filters.get(args, :min_matches)) || default_min_matches(matches)

      rows =
        matches
        |> team_ids()
        |> Enum.map(fn team_id ->
          relevant =
            Enum.filter(matches, fn match ->
              case venue do
                :home -> match.home_id == team_id
                :away -> match.away_id == team_id
                :all -> team_id in [match.home_id, match.away_id]
              end
            end)

          %{team: Graph.team(graph, team_id), record: record(relevant, team_id)}
        end)
        |> Enum.filter(&(&1.record.matches >= min_matches))
        |> Enum.sort_by(fn row -> {rank_value(row.record, sort_by), -row.record.points} end)

      {:ok,
       %{
         rankings: Enum.take(rows, limit),
         metric: venue,
         sort_by: sort_by,
         min_matches: min_matches,
         total_teams: length(rows),
         filters:
           %{competition: competition, season: season}
           |> Map.reject(fn {_, v} -> is_nil(v) end)
       }}
    end
  end

  # Fewest conceded is best, everything else is "more is better".
  defp rank_value(record, :goals_against), do: Map.fetch!(record, :goals_against)
  defp rank_value(record, key), do: -Map.fetch!(record, key)

  # Roughly a quarter of an average team's schedule, so one-off opponents do
  # not top the table with a single lucky win.
  defp default_min_matches(matches) do
    teams = max(length(team_ids(matches)), 1)
    max(5, div(div(2 * length(matches), teams), 4))
  end

  defp team_ids(matches) do
    matches
    |> Enum.flat_map(&[&1.home_id, &1.away_id])
    |> Enum.reject(&is_nil/1)
    |> Enum.uniq()
  end

  defp sort_key(nil), do: :win_rate

  defp sort_key(value) when is_binary(value) do
    case String.downcase(String.trim(value)) do
      "points" -> :points
      "wins" -> :wins
      "goals_for" -> :goals_for
      "goals_against" -> :goals_against
      "goal_difference" -> :goal_difference
      "matches" -> :matches
      _ -> :win_rate
    end
  end

  defp sort_key(value) when is_atom(value), do: value

  @doc """
  Aggregate a list of matches into a record from `team_id`'s point of view.
  """
  @spec record([Match.t()], binary) :: map
  def record(matches, team_id) do
    base = %{
      matches: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goals_for: 0,
      goals_against: 0
    }

    stats =
      Enum.reduce(matches, base, fn match, acc ->
        if Match.played?(match) and Match.side(match, team_id) do
          acc
          |> Map.update!(:matches, &(&1 + 1))
          |> Map.update!(:goals_for, &(&1 + Match.goals_for(match, team_id)))
          |> Map.update!(:goals_against, &(&1 + Match.goals_against(match, team_id)))
          |> then(fn acc ->
            case Match.outcome_for(match, team_id) do
              :win -> Map.update!(acc, :wins, &(&1 + 1))
              :draw -> Map.update!(acc, :draws, &(&1 + 1))
              :loss -> Map.update!(acc, :losses, &(&1 + 1))
              :unknown -> acc
            end
          end)
        else
          acc
        end
      end)

    played = stats.matches

    Map.merge(stats, %{
      goal_difference: stats.goals_for - stats.goals_against,
      points: stats.wins * 3 + stats.draws,
      win_rate: percentage(stats.wins, played),
      draw_rate: percentage(stats.draws, played),
      loss_rate: percentage(stats.losses, played),
      goals_for_avg: average(stats.goals_for, played),
      goals_against_avg: average(stats.goals_against, played),
      points_per_match: average(stats.wins * 3 + stats.draws, played)
    })
  end

  defp group_record(matches, team_id, key_fun) do
    matches
    |> Enum.group_by(key_fun)
    |> Enum.map(fn {key, list} -> {key, record(list, team_id)} end)
    |> Enum.sort_by(fn {key, _} -> key end)
  end

  defp form_entry(match, team_id) do
    %{
      match: match,
      outcome: Match.outcome_for(match, team_id),
      symbol:
        case Match.outcome_for(match, team_id) do
          :win -> "W"
          :draw -> "D"
          :loss -> "L"
          :unknown -> "?"
        end
    }
  end

  defp biggest(matches, team_id, outcome) do
    matches
    |> Enum.filter(&(Match.outcome_for(&1, team_id) == outcome))
    |> Enum.max_by(&Match.margin/1, fn -> nil end)
  end

  defp percentage(_part, 0), do: 0.0
  defp percentage(part, total), do: Float.round(part * 100 / total, 1)

  defp average(_part, 0), do: 0.0
  defp average(part, total), do: Float.round(part / total, 2)

  defp require_team(_graph, nil), do: {:error, {:missing_argument, :team}}
  defp require_team(graph, name), do: Graph.find_team(graph, name)

  defp to_map(args), do: Filters.atomize(args)
end
