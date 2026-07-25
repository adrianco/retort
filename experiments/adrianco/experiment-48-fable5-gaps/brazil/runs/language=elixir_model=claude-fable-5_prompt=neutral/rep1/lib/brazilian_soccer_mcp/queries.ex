defmodule BrazilianSoccerMcp.Queries do
  @moduledoc """
  Query and statistics engine over the loaded datasets: match search,
  head-to-head records, team statistics, league standings, player search,
  and aggregate competition statistics.
  """

  alias BrazilianSoccerMcp.{DataStore, Match, Player, TeamNames}

  # -- team resolution -------------------------------------------------------

  @doc """
  Resolve a user-supplied team name to the set of canonical team keys it could
  mean ("Flamengo" -> #{inspect(["flamengo-rj"])}, "América" -> América-MG and
  América-RN). Returns a MapSet (possibly empty).
  """
  def find_team_keys(query) do
    q = TeamNames.normalize(query)
    teams = Map.values(DataStore.teams())

    tiers = [
      fn t -> t.key == q.key end,
      fn t -> t.base == q.base and state_compatible?(q, t) end,
      fn t -> whole_word?(t.base, q.base) and state_compatible?(q, t) end,
      fn t -> String.contains?(t.base, q.base) end
    ]

    Enum.find_value(tiers, MapSet.new(), fn pred ->
      case Enum.filter(teams, pred) do
        [] -> nil
        hits -> MapSet.new(hits, & &1.key)
      end
    end)
  end

  defp state_compatible?(%{state: nil}, _t), do: true
  defp state_compatible?(%{state: s}, %{state: ts}), do: ts in [nil, s]

  defp whole_word?(_haystack, ""), do: false

  defp whole_word?(haystack, word),
    do: Regex.match?(~r/(^|\s)#{Regex.escape(word)}($|\s)/, haystack)

  # -- competitions ----------------------------------------------------------

  @doc "Normalize a competition query string to an internal competition atom."
  def normalize_competition(nil), do: nil

  def normalize_competition(s) do
    q = TeamNames.clean(to_string(s))

    cond do
      q == "" -> nil
      String.contains?(q, "libertadores") -> :libertadores
      String.contains?(q, "copa do brasil") -> :copa_do_brasil
      String.contains?(q, ["brazilian cup", "cup"]) -> :copa_do_brasil
      String.contains?(q, "serie b") -> :serie_b
      String.contains?(q, "serie c") -> :serie_c
      String.contains?(q, ["brasileir", "serie a", "campeonato"]) -> :brasileirao
      true -> :unknown
    end
  end

  def competition_label(:brasileirao), do: "Brasileirão Série A"
  def competition_label(:serie_b), do: "Série B"
  def competition_label(:serie_c), do: "Série C"
  def competition_label(:copa_do_brasil), do: "Copa do Brasil"
  def competition_label(:libertadores), do: "Copa Libertadores"
  def competition_label(other), do: to_string(other)

  # -- match search ----------------------------------------------------------

  @doc """
  Search matches. Options:

    * `:team`, `:opponent` - team name strings (opponent requires team)
    * `:competition`       - competition name string
    * `:season`            - integer year
    * `:date_from`, `:date_to` - `Date` bounds (inclusive)
    * `:stage`             - stage/round text filter (e.g. "final")

  Returns matches sorted most recent first.
  """
  def search_matches(opts \\ []) do
    team_keys = opts[:team] && find_team_keys(opts[:team])
    opp_keys = opts[:opponent] && find_team_keys(opts[:opponent])
    comp = normalize_competition(opts[:competition])

    DataStore.matches()
    |> filter_team(team_keys, opp_keys)
    |> filter(:competition, comp)
    |> filter(:season, opts[:season])
    |> filter_dates(opts[:date_from], opts[:date_to])
    |> filter_stage(opts[:stage])
    |> Enum.sort_by(& &1.date, {:desc, Date})
  end

  defp filter_team(matches, nil, _), do: matches

  defp filter_team(matches, team_keys, nil) do
    Enum.filter(matches, &(&1.home_key in team_keys or &1.away_key in team_keys))
  end

  defp filter_team(matches, team_keys, opp_keys) do
    Enum.filter(matches, fn m ->
      (m.home_key in team_keys and m.away_key in opp_keys) or
        (m.home_key in opp_keys and m.away_key in team_keys)
    end)
  end

  defp filter(matches, _field, nil), do: matches
  defp filter(matches, field, value), do: Enum.filter(matches, &(Map.get(&1, field) == value))

  defp filter_dates(matches, nil, nil), do: matches

  defp filter_dates(matches, from, to) do
    Enum.filter(matches, fn m ->
      (from == nil or Date.compare(m.date, from) != :lt) and
        (to == nil or Date.compare(m.date, to) != :gt)
    end)
  end

  defp filter_stage(matches, nil), do: matches

  defp filter_stage(matches, stage) do
    q = TeamNames.clean(stage)

    Enum.filter(matches, fn m ->
      s = TeamNames.clean("#{m.stage} #{m.round}")
      # "final" must not match "quarterfinals"/"semifinals"
      if q == "final",
        do: Regex.match?(~r/(^|\s)final(s)?($|\s)/, s),
        else: String.contains?(s, q)
    end)
  end

  # -- head to head ----------------------------------------------------------

  @doc "Head-to-head record between two teams across all competitions."
  def head_to_head(team1, team2, opts \\ []) do
    k1 = find_team_keys(team1)
    k2 = find_team_keys(team2)

    matches =
      search_matches(Keyword.take(opts, [:competition, :season]))
      |> Enum.filter(fn m ->
        (m.home_key in k1 and m.away_key in k2) or (m.home_key in k2 and m.away_key in k1)
      end)

    summary =
      Enum.reduce(
        matches,
        %{team1_wins: 0, team2_wins: 0, draws: 0, team1_goals: 0, team2_goals: 0},
        fn m, acc ->
          {g1, g2} =
            if m.home_key in k1, do: {m.home_goal, m.away_goal}, else: {m.away_goal, m.home_goal}

          acc = %{
            acc
            | team1_goals: acc.team1_goals + (g1 || 0),
              team2_goals: acc.team2_goals + (g2 || 0)
          }

          case Match.winner_key(m) do
            :draw ->
              %{acc | draws: acc.draws + 1}

            nil ->
              acc

            w ->
              if w in k1,
                do: %{acc | team1_wins: acc.team1_wins + 1},
                else: %{acc | team2_wins: acc.team2_wins + 1}
          end
        end
      )

    %{matches: matches, summary: summary, team1_keys: k1, team2_keys: k2}
  end

  # -- team statistics -------------------------------------------------------

  @doc """
  W/D/L, goals for/against, and per-competition breakdown for a team.
  Options: `:season`, `:competition`, `:venue` (`:home` | `:away` | `:all`).
  """
  def team_stats(team, opts \\ []) do
    keys = find_team_keys(team)
    venue = opts[:venue] || :all

    matches =
      search_matches(Keyword.take(opts, [:competition, :season]))
      |> Enum.filter(fn m ->
        case venue do
          :home -> m.home_key in keys
          :away -> m.away_key in keys
          :all -> m.home_key in keys or m.away_key in keys
        end
      end)

    stats = accumulate_stats(matches, keys)

    by_competition =
      matches
      |> Enum.group_by(& &1.competition)
      |> Map.new(fn {comp, ms} -> {comp, accumulate_stats(ms, keys)} end)

    %{keys: keys, matches: matches, stats: stats, by_competition: by_competition}
  end

  defp accumulate_stats(matches, keys) do
    matches
    |> Enum.filter(&(&1.home_goal != nil and &1.away_goal != nil))
    |> Enum.reduce(
      %{played: 0, wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0},
      fn m, acc ->
        {gf, ga} =
          if m.home_key in keys, do: {m.home_goal, m.away_goal}, else: {m.away_goal, m.home_goal}

        acc = %{
          acc
          | played: acc.played + 1,
            goals_for: acc.goals_for + (gf || 0),
            goals_against: acc.goals_against + (ga || 0)
        }

        case Match.winner_key(m) do
          :draw ->
            %{acc | draws: acc.draws + 1}

          nil ->
            acc

          w ->
            if w in keys, do: %{acc | wins: acc.wins + 1}, else: %{acc | losses: acc.losses + 1}
        end
      end
    )
  end

  # -- standings -------------------------------------------------------------

  @doc """
  League table for a season computed from match results (3 pts win, 1 draw).
  For the Brasileirão a single source file is used per season so matches are
  never double counted. Sorted by the Brazilian tiebreakers: points, wins,
  goal difference, goals for.
  """
  def standings(season, competition \\ :brasileirao) do
    matches =
      DataStore.matches()
      |> Enum.filter(&(&1.competition == competition and &1.season == season))
      |> restrict_source(competition, season)

    matches
    |> Enum.reduce(%{}, fn m, acc ->
      acc
      |> add_result(m.home_key, m.home_goal, m.away_goal)
      |> add_result(m.away_key, m.away_goal, m.home_goal)
    end)
    |> Enum.map(fn {key, row} ->
      row
      |> Map.put(:team, DataStore.display(key))
      |> Map.put(:key, key)
      |> Map.put(:goal_diff, row.goals_for - row.goals_against)
      |> Map.put(:points, row.wins * 3 + row.draws)
    end)
    |> Enum.sort_by(&{-&1.points, -&1.wins, -&1.goal_diff, -&1.goals_for, &1.team})
  end

  # Brasileirão seasons >= 2012 come from Brasileirao_Matches.csv, earlier
  # ones from the historical file; drop other sources for table calculation.
  defp restrict_source(matches, :brasileirao, season) do
    source = if season >= 2012, do: :serie_a, else: :historical

    case Enum.filter(matches, &(&1.source == source)) do
      [] -> matches
      picked -> picked
    end
  end

  defp restrict_source(matches, _comp, _season), do: matches

  defp add_result(acc, _key, nil, _), do: acc
  defp add_result(acc, _key, _, nil), do: acc

  defp add_result(acc, key, gf, ga) do
    row =
      Map.get(acc, key, %{played: 0, wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0})

    row = %{
      row
      | played: row.played + 1,
        goals_for: row.goals_for + gf,
        goals_against: row.goals_against + ga,
        wins: row.wins + if(gf > ga, do: 1, else: 0),
        draws: row.draws + if(gf == ga, do: 1, else: 0),
        losses: row.losses + if(gf < ga, do: 1, else: 0)
    }

    Map.put(acc, key, row)
  end

  # -- player search ---------------------------------------------------------

  @doc """
  Search FIFA players. Options: `:name`, `:nationality`, `:club`, `:position`,
  `:min_overall`, `:limit` (default 10). Sorted by overall rating descending.
  """
  def search_players(opts \\ []) do
    name = opts[:name] && TeamNames.clean(opts[:name])
    nationality = opts[:nationality] && TeamNames.clean(opts[:nationality])
    club = opts[:club] && TeamNames.clean(opts[:club])
    positions = opts[:position] && Player.position_codes(opts[:position])
    min_overall = opts[:min_overall]
    limit = opts[:limit] || 10

    DataStore.players()
    |> Enum.filter(fn p ->
      (name == nil or String.contains?(p.name_search, name)) and
        (nationality == nil or TeamNames.clean(p.nationality || "") == nationality) and
        (club == nil or String.contains?(p.club_search, club)) and
        (positions == nil or p.position in positions) and
        (min_overall == nil or (p.overall || 0) >= min_overall)
    end)
    |> Enum.sort_by(&{-(&1.overall || 0), &1.name})
    |> Enum.take(limit)
  end

  # -- aggregates ------------------------------------------------------------

  @doc "Matches with the largest winning margin. Options: `:competition`, `:season`, `:limit`."
  def biggest_wins(opts \\ []) do
    limit = opts[:limit] || 10

    search_matches(Keyword.take(opts, [:competition, :season, :team]))
    |> Enum.filter(&(Match.margin(&1) > 0))
    |> Enum.sort_by(&{-Match.margin(&1), -((&1.home_goal || 0) + (&1.away_goal || 0))})
    |> Enum.take(limit)
  end

  @doc """
  Aggregate statistics (match count, average goals, home/draw/away rates)
  for an optional competition/season filter.
  """
  def competition_stats(opts \\ []) do
    matches =
      search_matches(Keyword.take(opts, [:competition, :season]))
      |> Enum.filter(&(&1.home_goal != nil and &1.away_goal != nil))

    total = length(matches)

    {goals, home_wins, draws, away_wins} =
      Enum.reduce(matches, {0, 0, 0, 0}, fn m, {g, hw, d, aw} ->
        g = g + m.home_goal + m.away_goal

        cond do
          m.home_goal > m.away_goal -> {g, hw + 1, d, aw}
          m.home_goal < m.away_goal -> {g, hw, d, aw + 1}
          true -> {g, hw, d + 1, aw}
        end
      end)

    %{
      matches: total,
      total_goals: goals,
      avg_goals: ratio(goals, total),
      home_win_rate: percent(home_wins, total),
      draw_rate: percent(draws, total),
      away_win_rate: percent(away_wins, total),
      home_wins: home_wins,
      draws: draws,
      away_wins: away_wins
    }
  end

  def ratio(_num, 0), do: 0.0
  def ratio(num, den), do: Float.round(num / den, 2)

  def percent(_num, 0), do: 0.0
  def percent(num, den), do: Float.round(100.0 * num / den, 1)
end
