defmodule BrSoccer.Query do
  @moduledoc "Query and aggregation functions over the loaded match and player data."

  alias BrSoccer.{Data, Team}

  # ---------------------------------------------------------------- matches

  @doc """
  Filters matches. Options: :team, :opponent, :venue (home|away|any),
  :season, :competition, :date_from, :date_to, :stage, :round.
  """
  def matches(opts \\ []) do
    comp = Data.parse_competition(opts[:competition])
    from = Data.parse_date(opts[:date_from])
    to = Data.parse_date(opts[:date_to])
    season = Data.parse_int(opts[:season])
    team = opts[:team]
    opp = opts[:opponent]
    venue = opts[:venue] || "any"
    stage = opts[:stage] && String.downcase(opts[:stage])

    Data.matches()
    |> Enum.filter(fn m ->
      (comp == nil or m.competition == comp) and
        (season == nil or m.season == season) and
        (from == nil or Date.compare(m.date, from) != :lt) and
        (to == nil or Date.compare(m.date, to) != :gt) and
        (stage == nil or (m.stage != nil and String.downcase(m.stage) == stage)) and
        team_filter(m, team, opp, venue)
    end)
  end

  defp team_filter(_m, nil, nil, _), do: true
  defp team_filter(m, nil, opp, v), do: team_filter(m, opp, nil, v)

  defp team_filter(m, team, opp, venue) do
    home? = Team.matches?(m.home_key, team) and (opp == nil or Team.matches?(m.away_key, opp))
    away? = Team.matches?(m.away_key, team) and (opp == nil or Team.matches?(m.home_key, opp))

    case venue do
      "home" -> home?
      "away" -> away?
      _ -> home? or away?
    end
  end

  def result(m) do
    cond do
      m.home_goal > m.away_goal -> :home
      m.home_goal < m.away_goal -> :away
      true -> :draw
    end
  end

  @doc "Head-to-head summary between two teams."
  def head_to_head(a, b, opts \\ []) do
    ms = matches(Keyword.merge(opts, team: a, opponent: b)) |> Enum.filter(&scored?/1)

    Enum.reduce(ms, %{matches: ms, a_wins: 0, b_wins: 0, draws: 0, a_goals: 0, b_goals: 0}, fn m, acc ->
      a_home? = Team.matches?(m.home_key, a)
      {ag, bg} = if a_home?, do: {m.home_goal, m.away_goal}, else: {m.away_goal, m.home_goal}

      acc
      |> Map.update!(:a_goals, &(&1 + ag))
      |> Map.update!(:b_goals, &(&1 + bg))
      |> Map.update!(
        cond do
          ag > bg -> :a_wins
          ag < bg -> :b_wins
          true -> :draws
        end,
        &(&1 + 1)
      )
    end)
  end

  defp scored?(m), do: is_integer(m.home_goal) and is_integer(m.away_goal)

  # ---------------------------------------------------------------- teams

  @doc "Win/draw/loss record for a team. Options as in matches/1 (venue home|away|any)."
  def team_record(team, opts \\ []) do
    ms = matches(Keyword.put(opts, :team, team)) |> Enum.filter(&scored?/1)

    ms
    |> Enum.reduce(empty_record(), fn m, acc ->
      if Team.matches?(m.home_key, team) and opts[:venue] != "away",
        do: add(acc, m.home_goal, m.away_goal),
        else: add(acc, m.away_goal, m.home_goal)
    end)
    |> Map.put(:by_competition, ms |> Enum.frequencies_by(& &1.competition))
  end

  defp empty_record, do: %{played: 0, wins: 0, draws: 0, losses: 0, gf: 0, ga: 0}

  defp add(r, gf, ga) do
    %{
      r
      | played: r.played + 1,
        gf: r.gf + gf,
        ga: r.ga + ga,
        wins: r.wins + if(gf > ga, do: 1, else: 0),
        draws: r.draws + if(gf == ga, do: 1, else: 0),
        losses: r.losses + if(gf < ga, do: 1, else: 0)
    }
  end

  def win_rate(%{played: 0}), do: 0.0
  def win_rate(r), do: Float.round(r.wins * 100 / r.played, 1)

  @doc "Competitions (and seasons) a team appears in."
  def team_competitions(team) do
    matches(team: team)
    |> Enum.group_by(& &1.competition)
    |> Enum.map(fn {c, ms} -> {c, length(ms), ms |> Enum.map(& &1.season) |> Enum.uniq() |> Enum.sort()} end)
    |> Enum.sort_by(fn {_, n, _} -> -n end)
  end

  # ---------------------------------------------------------------- tables

  @doc "League table computed from results (3 pts win, 1 draw)."
  def standings(season, competition \\ "serie_a") do
    matches(season: season, competition: competition)
    |> Enum.filter(&scored?/1)
    |> Enum.reduce(%{}, fn m, acc ->
      acc
      |> Map.update(m.home_key, add(empty_record(), m.home_goal, m.away_goal), &add(&1, m.home_goal, m.away_goal))
      |> Map.update(m.away_key, add(empty_record(), m.away_goal, m.home_goal), &add(&1, m.away_goal, m.home_goal))
    end)
    |> Enum.map(fn {k, r} -> Map.merge(r, %{team: k, points: r.wins * 3 + r.draws, gd: r.gf - r.ga}) end)
    |> Enum.sort_by(&{-&1.points, -&1.wins, -&1.gd, -&1.gf})
  end

  @doc "Teams ranked by record across many matches (e.g. best home/away record)."
  def best_records(opts \\ []) do
    venue = opts[:venue] || "any"
    min = Data.parse_int(opts[:min_matches]) || 10

    matches(Keyword.drop(opts, [:venue]))
    |> Enum.filter(&scored?/1)
    |> Enum.reduce(%{}, fn m, acc ->
      acc =
        if venue in ["home", "any"],
          do: Map.update(acc, m.home_key, add(empty_record(), m.home_goal, m.away_goal), &add(&1, m.home_goal, m.away_goal)),
          else: acc

      if venue in ["away", "any"],
        do: Map.update(acc, m.away_key, add(empty_record(), m.away_goal, m.home_goal), &add(&1, m.away_goal, m.home_goal)),
        else: acc
    end)
    |> Enum.filter(fn {_, r} -> r.played >= min end)
    |> Enum.map(fn {k, r} -> Map.put(r, :team, k) end)
    |> Enum.sort_by(&{-win_rate(&1), -&1.played})
  end

  @doc "Aggregate statistics for a set of matches."
  def summary(opts \\ []) do
    ms = matches(opts) |> Enum.filter(&scored?/1)
    n = length(ms)
    goals = Enum.reduce(ms, 0, &(&1.home_goal + &1.away_goal + &2))
    freq = Enum.frequencies_by(ms, &result/1)

    pct = fn k -> if n == 0, do: 0.0, else: Float.round(Map.get(freq, k, 0) * 100 / n, 1) end

    %{
      matches: n,
      goals: goals,
      avg_goals: if(n == 0, do: 0.0, else: Float.round(goals / n, 2)),
      home_win_pct: pct.(:home),
      away_win_pct: pct.(:away),
      draw_pct: pct.(:draw)
    }
  end

  @doc "Largest victory margins."
  def biggest_wins(opts \\ []) do
    limit = Data.parse_int(opts[:limit]) || 10

    matches(opts)
    |> Enum.filter(&scored?/1)
    |> Enum.sort_by(&{-abs(&1.home_goal - &1.away_goal), -(&1.home_goal + &1.away_goal)})
    |> Enum.take(limit)
  end

  @doc "Team with most goals scored in a season/competition."
  def top_scoring_teams(opts) do
    opts
    |> Keyword.put_new(:competition, "serie_a")
    |> then(&standings(&1[:season], &1[:competition]))
    |> Enum.sort_by(&(-&1.gf))
  end

  @doc "Matches between traditional rivals."
  def derbies(opts \\ []) do
    matches(opts)
    |> Enum.flat_map(fn m ->
      case Team.derby(m.home_key, m.away_key) do
        nil -> []
        name -> [Map.put(m, :derby, name)]
      end
    end)
  end

  # ---------------------------------------------------------------- players

  @doc "Searches FIFA players. Options: :name, :nationality, :club, :position, :min_overall, :limit."
  def players(opts \\ []) do
    name = opts[:name] && opts[:name] |> Team.ascii() |> String.downcase()
    nat = opts[:nationality] && opts[:nationality] |> Team.ascii() |> String.downcase()
    club = opts[:club]
    pos = opts[:position] && position_set(opts[:position])
    min = Data.parse_int(opts[:min_overall])
    limit = Data.parse_int(opts[:limit])

    Data.players()
    |> Enum.filter(fn p ->
      (name == nil or name_match?(p.name_key, name)) and
        (nat == nil or (p.nationality || "") |> Team.ascii() |> String.downcase() == nat) and
        (club == nil or club_match?(p, club)) and
        (pos == nil or p.position in pos) and
        (min == nil or (p.overall || 0) >= min)
    end)
    |> Enum.sort_by(&(-(&1.overall || 0)))
    |> then(fn ps -> if limit, do: Enum.take(ps, limit), else: ps end)
  end

  defp name_match?(key, q), do: String.contains?(key, q) or Enum.all?(String.split(q), &String.contains?(key, &1))

  defp club_match?(%{club: nil}, _), do: false

  defp club_match?(p, club) do
    Team.matches?(p.club_key, club) or
      String.contains?(p.club |> Team.ascii() |> String.downcase(), club |> Team.ascii() |> String.downcase())
  end

  @position_groups %{
    "forward" => ~w(ST CF LF RF LW RW LS RS),
    "attacker" => ~w(ST CF LF RF LW RW LS RS),
    "striker" => ~w(ST CF LS RS),
    "midfielder" => ~w(CM CDM CAM LM RM LCM RCM LDM RDM LAM RAM),
    "defender" => ~w(CB LB RB LCB RCB LWB RWB),
    "goalkeeper" => ~w(GK)
  }

  defp position_set(pos) do
    key = pos |> String.downcase() |> String.trim_trailing("s")
    Map.get(@position_groups, key, [String.upcase(pos)])
  end

  @doc "Groups players of a nationality by club with counts and average ratings."
  def players_by_club(opts) do
    players(opts)
    |> Enum.group_by(& &1.club)
    |> Enum.reject(fn {c, _} -> is_nil(c) end)
    |> Enum.map(fn {c, ps} ->
      {c, length(ps), Float.round(Enum.sum(Enum.map(ps, & &1.overall)) / length(ps), 1)}
    end)
    |> Enum.sort_by(fn {_, n, avg} -> {-n, -avg} end)
  end
end
