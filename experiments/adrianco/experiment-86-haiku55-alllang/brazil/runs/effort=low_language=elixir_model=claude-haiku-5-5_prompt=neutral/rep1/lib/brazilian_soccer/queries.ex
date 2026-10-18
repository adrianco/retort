defmodule BrazilianSoccer.Queries do
  @moduledoc """
  Pure query functions over lists of `BrazilianSoccer.Match` and
  `BrazilianSoccer.Player`. Team arguments are plain names (any spelling the
  datasets use); they are normalized before matching.

  Shared filter options (keyword list, all optional):

    * `:season` - year, e.g. `2023`
    * `:competition` - substring of the competition name, folded for accents
      and case, e.g. `"libertadores"` or `"brasileirao serie a"`
    * `:date_from`, `:date_to` - `Date` bounds (inclusive)
  """

  alias BrazilianSoccer.Normalize

  @default_limit 20
  @default_standings_competition "brasileirao serie a"

  # Traditional rivalries as unordered pairs of team keys.
  @rivalries [
    {"flamengo", "fluminense"},
    {"corinthians", "palmeiras"},
    {"gremio", "internacional"},
    {"sao paulo", "corinthians"},
    {"sao paulo", "palmeiras"},
    {"santos", "sao paulo"},
    {"flamengo", "vasco"},
    {"flamengo", "botafogo"},
    {"atletico", "cruzeiro"},
    {"bahia", "vitoria"}
  ]

  @rivalry_set MapSet.new(@rivalries, fn {a, b} -> Enum.sort([a, b]) |> List.to_tuple() end)

  # metric name => {side of the match to count, summary field to rank by}
  @metrics %{
    "home_win_rate" => {:home, :win_rate},
    "away_win_rate" => {:away, :win_rate},
    "win_rate" => {:either, :win_rate},
    "wins" => {:either, :wins},
    "points" => {:either, :points},
    "goals_for" => {:either, :goals_for}
  }

  @position_groups %{
    "forward" => ~w(ST CF LW RW LF RF RS LS),
    "midfielder" => ~w(CM CAM CDM LM RM LCM RCM LDM RDM LAM RAM),
    "defender" => ~w(CB LB RB LWB RWB LCB RCB),
    "goalkeeper" => ~w(GK)
  }

  @doc "Metric names accepted by `ranking/3`."
  def ranking_metrics, do: Map.keys(@metrics)

  @doc """
  Finds matches involving a team, optionally restricted to one side, an
  opponent, a rivalry, and the shared filters. Newest first.

  Options: `:team`, `:side` (`:home | :away | :either`), `:opponent`,
  `:derby` (boolean), `:limit`, plus the shared filters.

  Returns `%{total: n, matches: [...]}` where `matches` is limited to `:limit`.
  """
  def find_matches(matches, opts \\ []) do
    filtered =
      matches
      |> scoped(opts)
      |> Enum.filter(&team_match?(&1, opts))
      |> Enum.sort_by(& &1.date, {:desc, Date})

    %{total: length(filtered), matches: Enum.take(filtered, limit(opts))}
  end

  @doc """
  Win/draw/loss record and goals for one team. Option `:side` restricts to
  home or away matches.
  """
  def team_record(matches, team, opts \\ []) do
    key = Normalize.team_key(team)

    rows =
      matches
      |> scoped(opts)
      |> entries()
      |> Enum.filter(&(&1.key == key and side_ok?(&1.side, opts[:side])))

    rows
    |> summarize()
    |> Map.merge(%{team: display_name(rows, team), side: opts[:side] || :either})
  end

  @doc """
  Head-to-head summary for two teams, with their meetings newest first.
  """
  def head_to_head(matches, team_a, team_b, opts \\ []) do
    key_a = Normalize.team_key(team_a)
    key_b = Normalize.team_key(team_b)

    games =
      matches
      |> scoped(opts)
      |> Enum.filter(&between?(&1, key_a, key_b))
      |> Enum.sort_by(& &1.date, {:desc, Date})

    rows = entries(games)
    rows_a = Enum.filter(rows, &(&1.key == key_a))
    rows_b = Enum.filter(rows, &(&1.key == key_b))
    summary_a = summarize(rows_a)
    summary_b = summarize(rows_b)

    %{
      team_a: display_name(rows_a, team_a),
      team_b: display_name(rows_b, team_b),
      played: length(games),
      wins_a: summary_a.wins,
      wins_b: summary_b.wins,
      draws: summary_a.draws,
      goals_a: summary_a.goals_for,
      goals_b: summary_b.goals_for,
      matches: games
    }
  end

  @doc """
  League table calculated from results (3 points for a win, 1 for a draw).
  Defaults to the Brasileirão Série A when no `:competition` is given.
  """
  def standings(matches, opts \\ []) do
    opts = Keyword.put_new(opts, :competition, @default_standings_competition)

    matches
    |> scoped(opts)
    |> entries()
    |> Enum.group_by(& &1.key)
    |> Enum.map(fn {_key, rows} -> Map.put(summarize(rows), :team, hd(rows).team) end)
    |> Enum.sort_by(&{-&1.points, -&1.wins, -&1.goal_difference, -&1.goals_for, &1.team})
  end

  @doc """
  Aggregate statistics: match count, goals per match, and home/away/draw
  percentages.
  """
  def league_stats(matches, opts \\ []) do
    games = scoped(matches, opts)
    played = length(games)
    total_goals = Enum.sum(Enum.map(games, &(&1.home_goals + &1.away_goals)))
    home_wins = Enum.count(games, &(&1.home_goals > &1.away_goals))
    away_wins = Enum.count(games, &(&1.away_goals > &1.home_goals))

    %{
      matches: played,
      total_goals: total_goals,
      avg_goals_per_match: if(played == 0, do: 0.0, else: Float.round(total_goals / played, 2)),
      home_win_rate: pct(home_wins, played),
      away_win_rate: pct(away_wins, played),
      draw_rate: pct(played - home_wins - away_wins, played)
    }
  end

  @doc "Matches with the largest winning margins (ties broken by total goals)."
  def biggest_wins(matches, opts \\ []) do
    matches
    |> scoped(opts)
    |> Enum.reject(&(&1.home_goals == &1.away_goals))
    |> Enum.sort_by(&{abs(&1.home_goals - &1.away_goals), &1.home_goals + &1.away_goals}, :desc)
    |> Enum.take(limit(opts, 5))
  end

  @doc """
  Teams ranked by a metric (see `ranking_metrics/0`). Only teams with at
  least `:min_matches` games (default 10) in the selected scope are included.
  Each row carries the ranked value in `:value`.
  """
  def ranking(matches, metric, opts \\ []) do
    {side, field} = Map.fetch!(@metrics, metric)
    min_matches = opts[:min_matches] || 10

    matches
    |> scoped(opts)
    |> entries()
    |> Enum.filter(&side_ok?(&1.side, side))
    |> Enum.group_by(& &1.key)
    |> Enum.map(fn {_key, rows} ->
      row = rows |> summarize() |> Map.put(:team, hd(rows).team)
      Map.put(row, :value, Map.fetch!(row, field))
    end)
    |> Enum.filter(&(&1.played >= min_matches))
    |> Enum.sort_by(&{&1.value, &1.played}, :desc)
    |> Enum.take(limit(opts))
  end

  @doc """
  Player search. Text options (`:name`, `:nationality`, `:club`) are
  case- and accent-insensitive substring matches. `:position` accepts a
  position code (`"ST"`) or a group (`"forward"`, `"midfielder"`,
  `"defender"`, `"goalkeeper"`). Sorted by overall rating, highest first.
  """
  def search_players(players, opts \\ []) do
    matched =
      Enum.filter(players, fn p ->
        text_contains?(p.name, opts[:name]) and
          text_contains?(p.nationality, opts[:nationality]) and
          text_contains?(p.club, opts[:club]) and
          position_ok?(p.position, opts[:position]) and
          (is_nil(opts[:min_overall]) or p.overall >= opts[:min_overall])
      end)

    %{
      total: length(matched),
      players: matched |> Enum.sort_by(& &1.overall, :desc) |> Enum.take(limit(opts))
    }
  end

  @doc "Position codes covered by a position group name, or the code itself."
  def positions_for(query) do
    key = query |> Normalize.fold() |> String.trim_trailing("s")
    Map.get(@position_groups, key, [String.upcase(String.trim(query))])
  end

  # --- internals ---

  # One row per team per match, from that team's point of view.
  defp entries(matches) do
    Enum.flat_map(matches, fn m ->
      [
        %{
          key: m.home_key,
          team: m.home,
          side: :home,
          gf: m.home_goals,
          ga: m.away_goals,
          match: m
        },
        %{
          key: m.away_key,
          team: m.away,
          side: :away,
          gf: m.away_goals,
          ga: m.home_goals,
          match: m
        }
      ]
    end)
  end

  defp summarize(rows) do
    played = length(rows)
    wins = Enum.count(rows, &(&1.gf > &1.ga))
    draws = Enum.count(rows, &(&1.gf == &1.ga))
    goals_for = Enum.sum(Enum.map(rows, & &1.gf))
    goals_against = Enum.sum(Enum.map(rows, & &1.ga))

    %{
      played: played,
      wins: wins,
      draws: draws,
      losses: played - wins - draws,
      goals_for: goals_for,
      goals_against: goals_against,
      goal_difference: goals_for - goals_against,
      points: 3 * wins + draws,
      win_rate: pct(wins, played)
    }
  end

  defp scoped(matches, opts) do
    competition = opts[:competition] && Normalize.fold(opts[:competition])

    Enum.filter(matches, fn m ->
      (is_nil(opts[:season]) or m.date.year == opts[:season]) and
        (is_nil(competition) or String.contains?(Normalize.fold(m.competition), competition)) and
        (is_nil(opts[:date_from]) or Date.compare(m.date, opts[:date_from]) != :lt) and
        (is_nil(opts[:date_to]) or Date.compare(m.date, opts[:date_to]) != :gt)
    end)
  end

  defp team_match?(match, opts) do
    team_ok =
      case opts[:team] do
        nil -> true
        team -> involved?(match, Normalize.team_key(team), opts[:side] || :either)
      end

    opponent_ok =
      case opts[:opponent] do
        nil -> true
        opponent -> involved?(match, Normalize.team_key(opponent), :either)
      end

    team_ok and opponent_ok and (!opts[:derby] or derby?(match))
  end

  defp involved?(match, key, :home), do: match.home_key == key
  defp involved?(match, key, :away), do: match.away_key == key
  defp involved?(match, key, _either), do: match.home_key == key or match.away_key == key

  defp between?(match, key_a, key_b) do
    (match.home_key == key_a and match.away_key == key_b) or
      (match.home_key == key_b and match.away_key == key_a)
  end

  defp derby?(match) do
    pair = Enum.sort([match.home_key, match.away_key]) |> List.to_tuple()
    MapSet.member?(@rivalry_set, pair)
  end

  defp side_ok?(_side, nil), do: true
  defp side_ok?(_side, :either), do: true
  defp side_ok?(side, wanted), do: side == wanted

  defp display_name([%{team: team} | _], _query), do: team
  defp display_name([], query), do: Normalize.display_name(query)

  defp text_contains?(_value, nil), do: true

  defp text_contains?(value, query),
    do: String.contains?(Normalize.fold(value || ""), Normalize.fold(query))

  defp position_ok?(_position, nil), do: true
  defp position_ok?(position, query), do: (position || "") in positions_for(query)

  defp pct(_part, 0), do: 0.0
  defp pct(part, whole), do: Float.round(part * 100 / whole, 1)

  defp limit(opts, default \\ @default_limit), do: opts[:limit] || default
end
