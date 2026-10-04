defmodule BrazilianSoccer.Queries do
  @moduledoc """
  Match, team and competition queries over the unified match list.

  Filters are passed as a map with optional keys:
  `:team`, `:opponent`, `:venue` ("home" | "away" | "either"), `:competition`,
  `:season`, `:date_from`, `:date_to`, `:stage`, `:round`.
  """

  alias BrazilianSoccer.{Loader, Match, Store, Teams, Text}

  # ── team references ────────────────────────────────────────────────────

  @doc """
  Resolves a user-supplied team name. When the normalised name is not a team
  in the data, falls back to the most frequent team whose name contains it
  (so "Atletico Paranaense", "Athletico-PR" and "Athletico" all work).
  """
  def team_ref(name) when is_binary(name) do
    ref = Teams.resolve(name)
    counts = Store.data().team_counts

    if Map.has_key?(counts, ref.key) or ref.key == "" do
      ref
    else
      counts
      |> Enum.filter(fn {key, _} -> word_match?(key, ref.key) end)
      |> Enum.max_by(&elem(&1, 1), fn -> nil end)
      |> case do
        nil -> ref
        {key, _} -> %{Teams.resolve(key) | state: ref.state} |> fill_name(key)
      end
    end
  end

  defp fill_name(ref, key) do
    # Use the spelling found in the data for display.
    m = Enum.find(Store.matches(), &(&1.home_key == key))
    resolved = Teams.resolve(key)

    %{
      ref
      | name: if(Teams.brazilian_club?(key), do: resolved.name, else: (m && m.home) || ref.name)
    }
  end

  defp word_match?(key, query) do
    String.contains?(" " <> key <> " ", " " <> query <> " ")
  end

  @doc "Which side (`:home`/`:away`) the referenced team plays in a match, or nil."
  def side(%Match{} = m, ref) do
    cond do
      Teams.same?(ref, m.home_key, m.home_state) -> :home
      Teams.same?(ref, m.away_key, m.away_state) -> :away
      true -> nil
    end
  end

  # ── competitions ───────────────────────────────────────────────────────

  @doc "Maps free text (\"Serie A\", \"brasileirao\", \"cup\") to a competition name."
  def competition(nil), do: nil

  def competition(name) do
    f = Text.fold(name)

    cond do
      f == "" -> nil
      f =~ "libertadores" -> "Copa Libertadores"
      f =~ "copa do brasil" or f =~ "cup" or f == "copa" -> "Copa do Brasil"
      f =~ ~r/serie b|second/ -> "Brasileirão Série B"
      f =~ ~r/serie c|third/ -> "Brasileirão Série C"
      f =~ ~r/brasileir|serie a|campeonato|league/ -> "Brasileirão Série A"
      true -> Enum.find(Loader.competitions(), name, &(Text.fold(&1) =~ f))
    end
  end

  # ── match search ───────────────────────────────────────────────────────

  @doc "Returns matches (newest first) satisfying the filters."
  def matches(filters \\ %{}) do
    team = filters[:team] && team_ref(filters[:team])
    opponent = filters[:opponent] && team_ref(filters[:opponent])
    venue = venue(filters[:venue])
    comp = competition(filters[:competition])
    season = Text.parse_int(filters[:season])
    from = Text.parse_date(filters[:date_from])
    to = Text.parse_date(filters[:date_to])
    stage = filters[:stage] && Text.fold(filters[:stage])
    round = Text.parse_int(filters[:round])

    Enum.filter(Store.matches(), fn m ->
      (comp == nil or m.competition == comp) and
        (season == nil or m.season == season) and
        (round == nil or m.round == round) and
        (from == nil or Date.compare(m.date, from) != :lt) and
        (to == nil or Date.compare(m.date, to) != :gt) and
        (stage == nil or stage_match?(m.stage, stage)) and
        teams_match?(m, team, opponent, venue)
    end)
  end

  defp venue(v) when v in ["home", :home], do: :home
  defp venue(v) when v in ["away", :away], do: :away
  defp venue(_), do: :either

  defp stage_match?(nil, _), do: false

  defp stage_match?(stage, q) do
    s = Text.fold(stage)
    # "final" must not match "semifinals"/"quarterfinals".
    if q in ["final", "finals"], do: s == "final", else: String.contains?(s, q)
  end

  defp teams_match?(_m, nil, nil, _), do: true

  defp teams_match?(m, team, nil, venue) do
    s = side(m, team)
    s != nil and (venue == :either or s == venue)
  end

  defp teams_match?(m, nil, opponent, venue),
    do: teams_match?(m, opponent, nil, flip(venue))

  defp teams_match?(m, team, opponent, venue) do
    s = side(m, team)

    s != nil and (venue == :either or s == venue) and
      case s do
        :home -> Teams.same?(opponent, m.away_key, m.away_state)
        :away -> Teams.same?(opponent, m.home_key, m.home_state)
      end
  end

  defp flip(:home), do: :away
  defp flip(:away), do: :home
  defp flip(v), do: v

  # ── records ────────────────────────────────────────────────────────────

  @zero %{matches: 0, wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0}

  @doc "Win/draw/loss record of a team over the given (played) matches."
  def record(matches, ref) do
    matches
    |> Enum.reduce(@zero, fn m, acc ->
      case Match.played?(m) && side(m, ref) do
        :home -> add(acc, m.home_goals, m.away_goals)
        :away -> add(acc, m.away_goals, m.home_goals)
        _ -> acc
      end
    end)
    |> finish()
  end

  defp add(acc, gf, ga) do
    acc = %{
      acc
      | matches: acc.matches + 1,
        goals_for: acc.goals_for + gf,
        goals_against: acc.goals_against + ga
    }

    cond do
      gf > ga -> %{acc | wins: acc.wins + 1}
      gf < ga -> %{acc | losses: acc.losses + 1}
      true -> %{acc | draws: acc.draws + 1}
    end
  end

  defp finish(r) do
    r
    |> Map.put(:points, r.wins * 3 + r.draws)
    |> Map.put(:goal_difference, r.goals_for - r.goals_against)
    |> Map.put(:win_rate, pct(r.wins, r.matches))
  end

  defp pct(_, 0), do: 0.0
  defp pct(n, d), do: Float.round(n * 100 / d, 1)

  @doc "Overall, home, away and per-competition records for a team."
  def team_stats(team, filters \\ %{}) do
    ref = team_ref(team)
    ms = filters |> Map.put(:team, team) |> Map.delete(:opponent) |> matches()
    played = Enum.filter(ms, &Match.played?/1)

    %{
      team: ref.name,
      overall: record(played, ref),
      home: played |> Enum.filter(&(side(&1, ref) == :home)) |> record(ref),
      away: played |> Enum.filter(&(side(&1, ref) == :away)) |> record(ref),
      by_competition:
        played
        |> Enum.group_by(& &1.competition)
        |> Enum.map(fn {c, cms} -> {c, record(cms, ref)} end)
        |> Enum.sort_by(fn {_, r} -> -r.matches end),
      seasons: played |> Enum.map(& &1.season) |> Enum.uniq() |> Enum.sort()
    }
  end

  @doc "Head-to-head summary between two teams."
  def head_to_head(team_a, team_b, filters \\ %{}) do
    a = team_ref(team_a)
    b = team_ref(team_b)
    ms = filters |> Map.merge(%{team: team_a, opponent: team_b}) |> matches()
    played = Enum.filter(ms, &Match.played?/1)

    %{
      team_a: a.name,
      team_b: b.name,
      derby: Teams.derby_name(a.key, b.key),
      matches: ms,
      record_a: record(played, a),
      record_b: record(played, b)
    }
  end

  @doc "Competitions (with seasons and record) a team appears in."
  def team_competitions(team) do
    ref = team_ref(team)

    %{team: team}
    |> matches()
    |> Enum.group_by(& &1.competition)
    |> Enum.map(fn {c, ms} ->
      %{
        competition: c,
        seasons: ms |> Enum.map(& &1.season) |> Enum.uniq() |> Enum.sort(),
        record: record(ms, ref)
      }
    end)
    |> Enum.sort_by(&(-&1.record.matches))
  end

  # ── tables ─────────────────────────────────────────────────────────────

  @doc """
  Builds a table of every team over the filtered matches. `venue` restricts
  each team's record to its home or away matches. Rows are sorted by points,
  wins, goal difference and goals scored (the Brasileirão tie-breakers).
  """
  def table(filters \\ %{}, venue \\ :either) do
    venue = venue(venue)

    filters
    |> Map.drop([:team, :opponent, :venue])
    |> matches()
    |> Enum.filter(&Match.played?/1)
    |> Enum.reduce(%{}, fn m, acc ->
      acc
      |> bump(
        venue in [:either, :home],
        m.home_key,
        m.home_state,
        m.home,
        m.home_goals,
        m.away_goals
      )
      |> bump(
        venue in [:either, :away],
        m.away_key,
        m.away_state,
        m.away,
        m.away_goals,
        m.home_goals
      )
    end)
    |> Enum.map(fn {_, {name, rec}} -> Map.put(finish(rec), :team, name) end)
    |> Enum.sort_by(&{-&1.points, -&1.wins, -&1.goal_difference, -&1.goals_for, &1.team})
  end

  defp bump(acc, false, _, _, _, _, _), do: acc

  defp bump(acc, true, key, state, name, gf, ga) do
    Map.update(acc, {key, state}, {name, add(@zero, gf, ga)}, fn {n, rec} ->
      {n, add(rec, gf, ga)}
    end)
  end

  @doc "League standings for a season, with champion/relegation annotations."
  def standings(season, competition \\ "Brasileirão Série A") do
    comp = competition(competition) || "Brasileirão Série A"
    season = Text.parse_int(season)
    rows = table(%{season: season, competition: comp})
    # Ignore stray rows (a handful of mislabelled fixtures in the source data).
    most = rows |> Enum.map(& &1.matches) |> Enum.max(fn -> 0 end)
    rows = Enum.filter(rows, &(&1.matches * 4 >= most))
    n = length(rows)
    played = div(Enum.sum(Enum.map(rows, & &1.matches)), 2)
    # A double round-robin; one missing fixture (e.g. a walkover) is tolerated.
    complete = n > 1 and played >= n * (n - 1) - 1
    league = comp =~ "Série"

    relegated =
      if league and comp != "Brasileirão Série C", do: relegation_slots(comp, season, n), else: 0

    rows =
      rows
      |> Enum.with_index(1)
      |> Enum.map(fn {r, pos} ->
        note =
          cond do
            not league or not complete -> nil
            pos == 1 -> "Champion"
            pos > n - relegated -> "Relegated"
            true -> nil
          end

        r |> Map.put(:position, pos) |> Map.put(:note, note)
      end)

    %{competition: comp, season: season, complete: complete, league: league, rows: rows}
  end

  # Serie A relegated two clubs in 2003 and four in every other season here.
  defp relegation_slots("Brasileirão Série A", 2003, _), do: 2
  defp relegation_slots(_, _, n) when n >= 16, do: 4
  defp relegation_slots(_, _, _), do: 0

  @doc "Ranks teams by a metric, requiring a minimum number of matches."
  def rankings(filters \\ %{}, opts \\ []) do
    sort_by = opts[:sort_by] || "win_rate"
    min = opts[:min_matches] || 10
    rows = filters |> table(filters[:venue]) |> Enum.filter(&(&1.matches >= min))

    case sort_by do
      "goals_against" -> Enum.sort_by(rows, &{&1.goals_against / &1.matches, -&1.matches})
      "goals_for" -> Enum.sort_by(rows, &{-&1.goals_for, &1.matches})
      "goal_difference" -> Enum.sort_by(rows, &{-&1.goal_difference, -&1.points})
      "wins" -> Enum.sort_by(rows, &{-&1.wins, -&1.points})
      "points" -> Enum.sort_by(rows, &{-&1.points, -&1.wins})
      "points_per_match" -> Enum.sort_by(rows, &{-&1.points / &1.matches, -&1.matches})
      _ -> Enum.sort_by(rows, &{-&1.wins / &1.matches, -&1.matches})
    end
  end

  # ── aggregate statistics ───────────────────────────────────────────────

  @doc "Aggregate statistics (goal averages, home/away win rates) for a set of matches."
  def summary(filters \\ %{}) do
    played = filters |> matches() |> Enum.filter(&Match.played?/1)
    n = length(played)
    goals = Enum.reduce(played, 0, &(&1.home_goals + &1.away_goals + &2))
    home_goals = Enum.reduce(played, 0, &(&1.home_goals + &2))
    home = Enum.count(played, &(&1.home_goals > &1.away_goals))
    away = Enum.count(played, &(&1.home_goals < &1.away_goals))
    with_corners = Enum.filter(played, &(&1.stats && &1.stats["total_corners"]))

    %{
      matches: n,
      goals: goals,
      home_goals: home_goals,
      away_goals: goals - home_goals,
      goals_per_match: if(n == 0, do: 0.0, else: Float.round(goals / n, 2)),
      home_wins: home,
      away_wins: away,
      draws: n - home - away,
      home_win_rate: pct(home, n),
      away_win_rate: pct(away, n),
      draw_rate: pct(n - home - away, n),
      avg_corners:
        case with_corners do
          [] -> nil
          l -> Float.round(Enum.reduce(l, 0, &(&1.stats["total_corners"] + &2)) / length(l), 2)
        end
    }
  end

  @doc "Matches with the largest goal margin."
  def biggest_wins(filters \\ %{}, limit \\ 10) do
    filters
    |> matches()
    |> Enum.filter(&Match.played?/1)
    |> Enum.sort_by(
      &{-abs(&1.home_goals - &1.away_goals), -(&1.home_goals + &1.away_goals),
       Date.to_erl(&1.date)}
    )
    |> Enum.take(limit)
  end

  @doc "Matches with the most goals."
  def highest_scoring(filters \\ %{}, limit \\ 10) do
    filters
    |> matches()
    |> Enum.filter(&Match.played?/1)
    |> Enum.sort_by(&{-(&1.home_goals + &1.away_goals), Date.to_erl(&1.date)})
    |> Enum.take(limit)
  end

  @doc "Matches between traditional rivals, as `{nickname, match}` tuples."
  def derbies(filters \\ %{}) do
    for m <- matches(filters),
        name = Teams.derby_name(m.home_key, m.away_key),
        Teams.brazilian_club?(m.home_key) and Teams.resolve(m.home_key).state == m.home_state,
        Teams.resolve(m.away_key).state == m.away_state,
        do: {name, m}
  end

  @doc "Side-by-side season comparison for a competition."
  def compare_seasons(season_a, season_b, competition \\ "Brasileirão Série A") do
    for s <- [season_a, season_b] do
      st = standings(s, competition)

      %{
        season: st.season,
        competition: st.competition,
        summary: summary(%{season: s, competition: st.competition}),
        top: Enum.take(st.rows, 4),
        complete: st.complete,
        best_attack: Enum.max_by(st.rows, & &1.goals_for, fn -> nil end),
        best_defense: Enum.min_by(st.rows, & &1.goals_against, fn -> nil end)
      }
    end
  end
end
