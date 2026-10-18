defmodule SoccerMcp.Query do
  @moduledoc """
  Pure queries over a `SoccerMcp.Store`.

  Every function returns plain data (matches, records, rows). Formatting for
  the LLM lives in `SoccerMcp.Format`, and tool argument handling lives in
  `SoccerMcp.Tools`.
  """

  alias SoccerMcp.{Match, Parse, Player, Store, Team}

  @default_limit 20

  @typedoc "Match filters. All keys are optional."
  @type match_opts :: [
          team: String.t(),
          opponent: String.t(),
          competition: String.t(),
          season: integer(),
          venue: :home | :away | :any,
          stage: String.t(),
          from: Date.t(),
          to: Date.t()
        ]

  @doc """
  Matches satisfying every filter, most recent first.

  `team` matches either side unless `venue` restricts it to home or away.
  `opponent` must be on the other side. `stage` matches a whole word in the
  stage or round, so `"final"` finds finals but not semifinals.
  """
  @spec find_matches(Store.t(), match_opts()) :: [Match.t()]
  def find_matches(%Store{matches: matches}, opts \\ []) do
    team = opts[:team] && Team.key(opts[:team])
    team_state = opts[:team] && Team.state(opts[:team])
    opponent = opts[:opponent] && Team.key(opts[:opponent])
    venue = Keyword.get(opts, :venue, :any)

    matches
    |> Enum.filter(fn m ->
      team_ok?(m, team, venue) and state_ok?(m, team, team_state) and
        opponent_ok?(m, team, opponent) and
        competition_ok?(m, opts[:competition]) and season_ok?(m, opts[:season]) and
        stage_ok?(m, opts[:stage]) and date_ok?(m, opts[:from], opts[:to])
    end)
    |> Enum.sort_by(& &1.date, {:desc, Date})
  end

  defp team_ok?(_m, nil, _venue), do: true
  defp team_ok?(m, key, :any), do: Match.involves?(m, key)
  defp team_ok?(m, key, :home), do: Match.home_for?(m, key)
  defp team_ok?(m, key, :away), do: Match.involves?(m, key) and not Match.home_for?(m, key)

  # "Atletico-GO" should not return Atlético-MG matches. A match with no
  # known state for that side is kept.
  defp state_ok?(_m, _team, nil), do: true
  defp state_ok?(_m, nil, _state), do: true

  defp state_ok?(m, team, state) do
    Team.compatible_states?(Match.side_state(m, team), state)
  end

  defp opponent_ok?(_m, _team, nil), do: true
  defp opponent_ok?(m, nil, opponent), do: Match.involves?(m, opponent)

  defp opponent_ok?(m, team, opponent) do
    (Team.matches?(m.home_key, team) and Team.matches?(m.away_key, opponent)) or
      (Team.matches?(m.away_key, team) and Team.matches?(m.home_key, opponent))
  end

  defp competition_ok?(_m, nil), do: true
  defp competition_ok?(m, competition), do: m.competition == competition

  defp season_ok?(_m, nil), do: true
  defp season_ok?(m, season), do: m.season == season

  defp stage_ok?(_m, nil), do: true
  defp stage_ok?(%Match{stage: nil}, _stage), do: false
  defp stage_ok?(m, stage), do: Team.matches?(Team.key(m.stage), Team.key(stage))

  defp date_ok?(m, from, to) do
    (is_nil(from) or Date.compare(m.date, from) != :lt) and
      (is_nil(to) or Date.compare(m.date, to) != :gt)
  end

  @doc """
  Win, draw and loss record for the team with `key`, from `matches`.

  Each match is counted from that team's side. Win rate is a percentage
  rounded to one decimal place, or `0.0` with no matches.
  """
  @spec record([Match.t()], String.t()) :: map()
  def record(matches, key) do
    outcomes =
      for m <- matches, Match.involves?(m, key) do
        {gf, ga} = Match.goals_for_against(m, key)
        {outcome(gf, ga), gf, ga}
      end

    wins = Enum.count(outcomes, &match?({:win, _, _}, &1))
    draws = Enum.count(outcomes, &match?({:draw, _, _}, &1))
    losses = Enum.count(outcomes, &match?({:loss, _, _}, &1))
    played = wins + draws + losses

    %{
      played: played,
      wins: wins,
      draws: draws,
      losses: losses,
      goals_for: Enum.sum(Enum.map(outcomes, &elem(&1, 1))),
      goals_against: Enum.sum(Enum.map(outcomes, &elem(&1, 2))),
      win_rate: percent(wins, played),
      points: 3 * wins + draws
    }
  end

  defp outcome(gf, ga) when gf > ga, do: :win
  defp outcome(gf, ga) when gf < ga, do: :loss
  defp outcome(_gf, _ga), do: :draw

  @doc """
  Matches between two teams, in either venue, most recent first.
  """
  @spec head_to_head(Store.t(), String.t(), String.t(), keyword()) :: [Match.t()]
  def head_to_head(%Store{} = store, team_a, team_b, opts \\ []) do
    find_matches(store, Keyword.merge([team: team_a, opponent: team_b], opts))
  end

  @doc """
  League table for one competition and season, calculated from results.

  Uses exact team keys, so a row is one club. Points are 3 for a win and 1
  for a draw. Rows are sorted by points, goal difference, then goals scored.
  """
  @spec standings([Match.t()]) :: [map()]
  def standings(matches) do
    matches
    |> Enum.reduce(%{}, fn m, table ->
      table
      |> add_side({m.home_key, m.home_state}, m.home, m.home_goals, m.away_goals)
      |> add_side({m.away_key, m.away_state}, m.away, m.away_goals, m.home_goals)
    end)
    |> Map.values()
    |> label_ambiguous_names()
    |> Enum.map(fn row ->
      Map.merge(row, %{
        goal_difference: row.goals_for - row.goals_against,
        points: 3 * row.wins + row.draws,
        win_rate: percent(row.wins, row.played)
      })
    end)
    |> Enum.sort_by(&{-&1.points, -&1.goal_difference, -&1.goals_for, &1.team})
  end

  # Two clubs can share a display name in different states. Add the state to
  # both labels so the table can tell them apart.
  defp label_ambiguous_names(rows) do
    counts = Enum.frequencies_by(rows, & &1.team)

    Enum.map(rows, fn row ->
      if counts[row.team] > 1 and row.state do
        %{row | team: "#{row.team} (#{String.upcase(row.state)})"}
      else
        row
      end
    end)
  end

  defp add_side(table, {_key, state} = id, name, gf, ga) do
    row =
      Map.get(table, id, %{
        team: name,
        state: state,
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goals_for: 0,
        goals_against: 0
      })

    row = %{
      row
      | played: row.played + 1,
        goals_for: row.goals_for + gf,
        goals_against: row.goals_against + ga
    }

    row =
      case outcome(gf, ga) do
        :win -> %{row | wins: row.wins + 1}
        :draw -> %{row | draws: row.draws + 1}
        :loss -> %{row | losses: row.losses + 1}
      end

    Map.put(table, id, row)
  end

  @doc """
  Summary statistics over a set of matches: count, goals per match, and the
  share of home wins, draws and away wins.
  """
  @spec averages([Match.t()]) :: map()
  def averages(matches) do
    count = length(matches)
    goals = Enum.sum(Enum.map(matches, &(&1.home_goals + &1.away_goals)))
    home_wins = Enum.count(matches, &(&1.home_goals > &1.away_goals))
    draws = Enum.count(matches, &(&1.home_goals == &1.away_goals))
    away_wins = count - home_wins - draws

    %{
      matches: count,
      goals_per_match: if(count == 0, do: 0.0, else: Float.round(goals / count, 2)),
      home_win_rate: percent(home_wins, count),
      draw_rate: percent(draws, count),
      away_win_rate: percent(away_wins, count)
    }
  end

  @doc "The `n` matches with the largest winning margin, then most goals."
  @spec biggest_wins([Match.t()], pos_integer()) :: [Match.t()]
  def biggest_wins(matches, n \\ @default_limit) do
    matches
    |> Enum.reject(&(&1.home_goals == &1.away_goals))
    |> Enum.sort_by(
      &{-abs(&1.home_goals - &1.away_goals), -(&1.home_goals + &1.away_goals), &1.date},
      :asc
    )
    |> Enum.take(n)
  end

  @doc """
  Teams ranked by win rate at one venue. `venue` is `:home` or `:away`.

  Only teams with at least `min_played` matches at that venue are ranked.
  """
  @spec venue_ranking([Match.t()], :home | :away, non_neg_integer()) :: [map()]
  def venue_ranking(matches, venue, min_played \\ 5) do
    matches
    |> Enum.group_by(fn m -> if venue == :home, do: m.home_key, else: m.away_key end)
    |> Enum.map(fn {key, ms} ->
      ms
      |> record(key)
      |> Map.put(:team, display_name(ms, venue))
    end)
    |> Enum.filter(&(&1.played >= min_played))
    |> Enum.sort_by(&{-&1.win_rate, -&1.wins, &1.team})
  end

  defp display_name([first | _], :home), do: first.home
  defp display_name([first | _], :away), do: first.away

  @doc """
  Players matching every filter, highest overall first.

  Options: `:name` (substring of the player name), `:nationality`, `:club`
  (substring of the club), `:position` (exact, e.g. `"ST"`), `:min_overall`.
  Text matching ignores case and accents.
  """
  @spec players(Store.t(), keyword()) :: [Player.t()]
  def players(%Store{players: players}, opts \\ []) do
    players
    |> Enum.filter(fn p ->
      contains?(p.name, opts[:name]) and
        contains?(p.nationality, opts[:nationality]) and
        contains?(p.club, opts[:club]) and
        position_ok?(p, opts[:position]) and
        overall_ok?(p, opts[:min_overall])
    end)
    |> Enum.sort_by(&{-(&1.overall || 0), &1.name})
    |> Enum.take(Keyword.get(opts, :limit, @default_limit))
  end

  defp contains?(_text, nil), do: true
  defp contains?(nil, _query), do: false
  defp contains?(text, query), do: String.contains?(Parse.fold(text), Parse.fold(query))

  defp position_ok?(_p, nil), do: true
  defp position_ok?(%Player{position: nil}, _), do: false
  defp position_ok?(p, position), do: String.upcase(p.position) == String.upcase(position)

  defp overall_ok?(_p, nil), do: true
  defp overall_ok?(p, min), do: (p.overall || 0) >= min

  @doc "Default number of results returned when a caller gives no limit."
  def default_limit, do: @default_limit

  defp percent(_part, 0), do: 0.0
  defp percent(part, whole), do: Float.round(part / whole * 100, 1)
end
