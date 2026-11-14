defmodule BrazilianSoccer.Queries do
  @moduledoc """
  Query layer over `BrazilianSoccer.Data`: match search, team records,
  head-to-head, standings, rankings, aggregate statistics and player search.

  Functions take the dataset as first argument and a keyword list / map of
  filters. Team and competition names are free text and are normalised here.
  """

  alias BrazilianSoccer.{Data, TeamNames, Text}

  @empty %{matches: 0, wins: 0, draws: 0, losses: 0, goals_for: 0, goals_against: 0}

  @position_groups %{
    "forward" => ~w(ST CF LF RF LS RS LW RW),
    "midfielder" => ~w(CM LCM RCM CAM LAM RAM CDM LDM RDM LM RM),
    "defender" => ~w(CB LCB RCB LB RB LWB RWB),
    "goalkeeper" => ~w(GK)
  }

  # ------------------------------------------------------------ resolution

  @doc "Resolves free-text team name to a canonical team key."
  def resolve_team(%Data{teams: teams}, name) when is_binary(name) do
    {base, state, _} = TeamNames.parse(name)

    key =
      if state == nil or match?(%{state: ^state}, teams[base]),
        do: base,
        else: base <> "-" <> String.downcase(state)

    cond do
      Map.has_key?(teams, key) ->
        {:ok, key}

      Map.has_key?(teams, base) ->
        {:ok, base}

      true ->
        n = TeamNames.clean(name)

        candidates =
          for {k, t} <- teams,
              n != "",
              String.contains?(k, n) or String.contains?(TeamNames.clean(t.name), n),
              do: t

        case candidates do
          [] ->
            {:error,
             "Team not found: #{inspect(name)}. Use list_teams to search available team names."}

          list ->
            {:ok, Enum.max_by(list, & &1.matches).key}
        end
    end
  end

  def resolve_team(_, other), do: {:error, "Invalid team name: #{inspect(other)}"}

  @doc "Resolves free-text competition name to its canonical name."
  def resolve_competition(name) when is_binary(name) do
    n = Text.normalize(name)
    [a, b, c, cup, lib] = Data.competitions()

    cond do
      n =~ "libertadores" ->
        {:ok, lib}

      n =~ "copa do brasil" or n =~ "cup" or n == "copa" ->
        {:ok, cup}

      n =~ ~r/serie b|second division|segunda/ ->
        {:ok, b}

      n =~ ~r/serie c|third division|terceira/ ->
        {:ok, c}

      n =~ ~r/brasileir|serie a|campeonato brasileiro/ or n in ["league", "campeonato"] ->
        {:ok, a}

      true ->
        {:error,
         "Unknown competition: #{inspect(name)}. Known: #{Enum.join(Data.competitions(), ", ")}"}
    end
  end

  def resolve_competition(other), do: {:error, "Invalid competition: #{inspect(other)}"}

  def team_name(%Data{teams: teams}, key), do: teams[key].name

  # --------------------------------------------------------------- matches

  @doc """
  Finds matches (newest first). Filters: `:team`, `:opponent`, `:venue`
  ("home" | "away" | "any", relative to `:team`), `:competition`, `:season`,
  `:date_from`, `:date_to`, `:round`, `:stage`.
  """
  def matches(%Data{} = data, filters \\ []) do
    f = Map.new(filters) |> Map.reject(fn {_, v} -> v in [nil, ""] end)

    with {:ok, team} <- opt(f, :team, &resolve_team(data, &1)),
         {:ok, opp} <- opt(f, :opponent, &resolve_team(data, &1)),
         {:ok, comp} <- opt(f, :competition, &resolve_competition/1),
         {:ok, from} <- opt(f, :date_from, &date/1),
         {:ok, to} <- opt(f, :date_to, &date/1),
         {:ok, venue} <- venue(f[:venue]) do
      season = Text.to_int(f[:season])
      round = f[:round] && to_string(f[:round])
      stage = f[:stage] && stage_key(f[:stage])

      {:ok,
       Enum.filter(data.matches, fn m ->
         (comp == nil or m.competition == comp) and
           (season == nil or m.season == season) and
           team_ok?(m, team, opp, venue) and
           (from == nil or Date.compare(m.date, from) != :lt) and
           (to == nil or Date.compare(m.date, to) != :gt) and
           (round == nil or to_string(m.round) == round or stage_key(m.stage) == stage_key(round)) and
           (stage == nil or stage_key(m.stage) == stage)
       end)}
    end
  end

  defp opt(f, k, fun) do
    case Map.get(f, k) do
      nil -> {:ok, nil}
      v -> fun.(v)
    end
  end

  defp date(%Date{} = d), do: {:ok, d}

  defp date(s) do
    case Text.parse_date(to_string(s)) do
      nil -> {:error, "Invalid date: #{inspect(s)} (use YYYY-MM-DD or DD/MM/YYYY)"}
      d -> {:ok, d}
    end
  end

  defp venue(v) when v in [nil, "any", "either", "all", :any], do: {:ok, :any}
  defp venue(v) when v in ["home", :home], do: {:ok, :home}
  defp venue(v) when v in ["away", :away], do: {:ok, :away}
  defp venue(v), do: {:error, "Invalid venue: #{inspect(v)} (use home, away or any)"}

  defp stage_key(nil), do: nil

  defp stage_key(s),
    do:
      s
      |> to_string()
      |> Text.normalize()
      |> String.replace(~r/[\s-]/, "")
      |> String.trim_trailing("s")

  defp team_ok?(_m, nil, nil, _), do: true
  defp team_ok?(m, nil, opp, _), do: m.home == opp or m.away == opp

  defp team_ok?(m, team, opp, venue) do
    case venue do
      :home ->
        m.home == team and (opp == nil or m.away == opp)

      :away ->
        m.away == team and (opp == nil or m.home == opp)

      :any ->
        (m.home == team and (opp == nil or m.away == opp)) or
          (m.away == team and (opp == nil or m.home == opp))
    end
  end

  # --------------------------------------------------------------- records

  @doc "Win/draw/loss/goals record of `team_key` over `matches`."
  def record(matches, team_key) do
    Enum.reduce(matches, @empty, fn m, acc ->
      cond do
        m.home == team_key -> add(acc, m.home_goals, m.away_goals)
        m.away == team_key -> add(acc, m.away_goals, m.home_goals)
        true -> acc
      end
    end)
    |> finish()
  end

  defp add(acc, gf, ga) do
    %{
      acc
      | matches: acc.matches + 1,
        wins: acc.wins + if(gf > ga, do: 1, else: 0),
        draws: acc.draws + if(gf == ga, do: 1, else: 0),
        losses: acc.losses + if(gf < ga, do: 1, else: 0),
        goals_for: acc.goals_for + gf,
        goals_against: acc.goals_against + ga
    }
  end

  defp finish(r) do
    points = r.wins * 3 + r.draws

    r
    |> Map.put(:points, points)
    |> Map.put(:goal_difference, r.goals_for - r.goals_against)
    |> Map.put(:win_rate, pct(r.wins, r.matches))
    |> Map.put(
      :points_per_game,
      if(r.matches > 0, do: Float.round(points / r.matches, 2), else: 0.0)
    )
  end

  defp pct(_, 0), do: 0.0
  defp pct(a, b), do: Float.round(a * 100 / b, 1)

  @doc "Team statistics (overall, home, away, per competition) with the same filters as `matches/2`."
  def team_stats(%Data{} = data, team, filters \\ []) do
    with {:ok, key} <- resolve_team(data, team),
         {:ok, ms} <- matches(data, filters |> Map.new() |> Map.put(:team, team)) do
      home = Enum.filter(ms, &(&1.home == key))
      away = Enum.filter(ms, &(&1.away == key))

      {:ok,
       %{
         team: team_name(data, key),
         key: key,
         overall: record(ms, key),
         home: record(home, key),
         away: record(away, key),
         by_competition:
           ms
           |> Enum.group_by(& &1.competition)
           |> Enum.map(fn {c, l} -> {c, record(l, key)} end)
           |> Enum.sort(),
         seasons: ms |> Enum.map(& &1.season) |> Enum.uniq() |> Enum.sort(),
         matches: ms
       }}
    end
  end

  @doc "Head-to-head record between two teams (optional match filters)."
  def head_to_head(%Data{} = data, team_a, team_b, filters \\ []) do
    with {:ok, a} <- resolve_team(data, team_a),
         {:ok, b} <- resolve_team(data, team_b),
         {:ok, ms} <-
           matches(data, filters |> Map.new() |> Map.merge(%{team: team_a, opponent: team_b})) do
      rec = record(ms, a)

      {:ok,
       %{
         team_a: team_name(data, a),
         team_b: team_name(data, b),
         key_a: a,
         key_b: b,
         matches: ms,
         total: rec.matches,
         a_wins: rec.wins,
         b_wins: rec.losses,
         draws: rec.draws,
         a_goals: rec.goals_for,
         b_goals: rec.goals_against
       }}
    end
  end

  # ------------------------------------------------------------- standings

  @doc """
  League table calculated from results (3 points per win; ties broken by wins,
  goal difference, goals scored). Returns rows with `:position`, `:team`,
  record fields and `:note` ("Champion" / "Relegated") for complete seasons.
  """
  def standings(%Data{} = data, competition, season) do
    with {:ok, comp} <- resolve_competition(competition),
         true <-
           Data.league?(comp) ||
             {:error, "#{comp} is a knockout competition; use knockout_bracket instead."},
         season when is_integer(season) <-
           Text.to_int(season) || {:error, "A season (year) is required."},
         {:ok, ms} <- matches(data, competition: comp, season: season) do
      table = table(data, ms, :any)
      max_played = table |> Enum.map(& &1.matches) |> Enum.max(fn -> 0 end)
      # ignore stray teams from noisy rows (a club with a couple of games in a 38-round league)
      table = Enum.filter(table, &(&1.matches * 4 >= max_played))
      n = length(table)
      complete? = n > 1 and Enum.all?(table, &(&1.matches == 2 * (n - 1)))
      relegated = if comp == hd(Data.competitions()), do: relegation_spots(season, n), else: 0

      rows =
        table
        |> Enum.with_index(1)
        |> Enum.map(fn {r, i} ->
          note =
            cond do
              not complete? -> nil
              i == 1 -> "Champion"
              i > n - relegated -> "Relegated"
              true -> nil
            end

          r |> Map.put(:position, i) |> Map.put(:note, note)
        end)

      if rows == [] do
        {:error, "No #{comp} matches for season #{season} in the dataset."}
      else
        {:ok,
         %{
           competition: comp,
           season: season,
           complete: complete?,
           rows: rows,
           matches: length(ms)
         }}
      end
    end
  end

  defp relegation_spots(2003, _), do: 2
  defp relegation_spots(_, n) when n >= 20, do: 4
  defp relegation_spots(_, _), do: 0

  defp table(data, ms, venue) do
    ms
    |> Enum.reduce(%{}, fn m, acc ->
      acc =
        if venue in [:any, :home],
          do:
            Map.update(
              acc,
              m.home,
              add(@empty, m.home_goals, m.away_goals),
              &add(&1, m.home_goals, m.away_goals)
            ),
          else: acc

      if venue in [:any, :away],
        do:
          Map.update(
            acc,
            m.away,
            add(@empty, m.away_goals, m.home_goals),
            &add(&1, m.away_goals, m.home_goals)
          ),
        else: acc
    end)
    |> Enum.map(fn {k, r} -> r |> finish() |> Map.merge(%{key: k, team: team_name(data, k)}) end)
    |> Enum.sort_by(&{-&1.points, -&1.wins, -&1.goal_difference, -&1.goals_for, &1.team})
  end

  @metrics ~w(win_rate points_per_game points wins draws losses goals_for goals_against goal_difference matches)

  @doc """
  Ranks teams over the filtered matches. Options: `:venue`, `:metric`
  (#{Enum.join(@metrics, ", ")}), `:order` ("desc" | "asc"), `:min_matches`.
  """
  def rankings(%Data{} = data, filters \\ []) do
    f = Map.new(filters)
    metric = to_string(f[:metric] || "win_rate")

    with true <-
           metric in @metrics ||
             {:error,
              "Unknown metric #{inspect(metric)}. Use one of: #{Enum.join(@metrics, ", ")}"},
         {:ok, venue} <- venue(f[:venue]),
         {:ok, ms} <-
           matches(data, Map.drop(f, [:venue, :metric, :order, :min_matches, :team, :opponent])) do
      metric = String.to_existing_atom(metric)
      min = Text.to_int(f[:min_matches]) || default_min(ms)
      desc? = to_string(f[:order] || "desc") != "asc"

      rows =
        data
        |> table(ms, venue)
        |> Enum.filter(&(&1.matches >= min))
        |> Enum.sort_by(fn r ->
          v = Map.fetch!(r, metric)
          {if(desc?, do: -v, else: v), -r.matches, r.team}
        end)

      {:ok, %{rows: rows, metric: metric, venue: venue, min_matches: min, matches: length(ms)}}
    end
  end

  # Teams need a meaningful sample to be ranked on rates.
  defp default_min(ms) do
    seasons = ms |> Enum.map(&{&1.competition, &1.season}) |> Enum.uniq() |> length()
    if seasons <= 1, do: 5, else: 20
  end

  # ------------------------------------------------------------ aggregates

  @doc "Aggregate statistics over the filtered matches."
  def summary(%Data{} = data, filters \\ []) do
    with {:ok, ms} <- matches(data, filters), do: {:ok, summarize(ms)}
  end

  def summarize(ms) do
    n = length(ms)
    goals = Enum.reduce(ms, 0, &(&1.home_goals + &1.away_goals + &2))
    home_goals = Enum.reduce(ms, 0, &(&1.home_goals + &2))
    hw = Enum.count(ms, &(&1.home_goals > &1.away_goals))
    dr = Enum.count(ms, &(&1.home_goals == &1.away_goals))

    %{
      matches: n,
      goals: goals,
      home_goals: home_goals,
      away_goals: goals - home_goals,
      avg_goals: if(n > 0, do: Float.round(goals / n, 2), else: 0.0),
      home_wins: hw,
      draws: dr,
      away_wins: n - hw - dr,
      home_win_rate: pct(hw, n),
      draw_rate: pct(dr, n),
      away_win_rate: pct(n - hw - dr, n)
    }
  end

  @doc "Largest winning margins among the filtered matches."
  def biggest_wins(%Data{} = data, filters \\ [], limit \\ 10) do
    with {:ok, ms} <- matches(data, filters) do
      {:ok,
       ms
       |> Enum.filter(&(&1.home_goals != &1.away_goals))
       |> Enum.sort_by(
         &{-abs(&1.home_goals - &1.away_goals), -(&1.home_goals + &1.away_goals),
          -Date.to_gregorian_days(&1.date)}
       )
       |> Enum.take(limit)}
    end
  end

  @doc "Matches between traditional rivals, as `{nickname, match}` (newest first)."
  def derbies(%Data{} = data, filters \\ []) do
    pairs =
      for {a, b, nick} <- TeamNames.derbies(),
          {:ok, ka} <- [resolve_team(data, a)],
          {:ok, kb} <- [resolve_team(data, b)],
          into: %{},
          do: {Enum.sort([ka, kb]), nick}

    with {:ok, ms} <- matches(data, filters) do
      {:ok, for(m <- ms, nick = pairs[Enum.sort([m.home, m.away])], do: {nick, m})}
    end
  end

  @doc "Knockout rounds of a cup season grouped by round/stage, in playing order."
  def bracket(%Data{} = data, competition, season) do
    with {:ok, comp} <- resolve_competition(competition),
         false <- Data.league?(comp) && {:error, "#{comp} is a league; use standings instead."},
         {:ok, ms} <- matches(data, competition: comp, season: season) do
      rounds =
        ms
        |> Enum.reverse()
        |> Enum.chunk_by(&round_label/1)
        |> Enum.group_by(&round_label(hd(&1)))
        |> Enum.map(fn {label, chunks} -> {label, List.flatten(chunks)} end)
        |> Enum.sort_by(fn {_, l} -> Date.to_gregorian_days(List.last(l).date) end)

      final = Enum.filter(ms, &(stage_key(&1.stage) == "final"))

      {:ok,
       %{
         competition: comp,
         season: Text.to_int(season),
         rounds: rounds,
         champion: champion(data, final)
       }}
    end
  end

  def round_label(m) do
    cond do
      m.stage -> m.stage
      m.round -> "Round #{m.round}"
      true -> "Round not recorded"
    end
  end

  # Winner of a one- or two-legged final on aggregate; nil when level
  # (penalties / away goals are not in the data) or when there is no final.
  defp champion(_data, []), do: nil

  defp champion(data, [m | _] = final) do
    {a, b} = {m.home, m.away}
    r = record(final, a)

    cond do
      r.goals_for > r.goals_against -> team_name(data, a)
      r.goals_for < r.goals_against -> team_name(data, b)
      true -> nil
    end
  end

  # --------------------------------------------------------------- players

  @doc """
  Searches players. Filters: `:name`, `:nationality`, `:club`, `:position`
  (code such as "ST" or group forward/midfielder/defender/goalkeeper),
  `:min_overall`, `:max_age`, `:brazilian_clubs` (boolean), `:sort_by`
  ("overall" | "potential" | "age" | "name").
  """
  def players(%Data{} = data, filters \\ []) do
    f = Map.new(filters) |> Map.reject(fn {_, v} -> v in [nil, ""] end)
    name = f[:name] && Text.normalize(f[:name]) |> String.split(" ", trim: true)
    nat = f[:nationality] && nationality(f[:nationality])
    club = f[:club] && Text.normalize(f[:club])

    club_key =
      case f[:club] && resolve_team(data, f[:club]) do
        {:ok, k} -> k
        _ -> nil
      end

    # Prefer the exact club ("Santos") over substring hits ("Santos Laguna").
    linked? = club_key != nil and Enum.any?(data.players, &(&1.club_key == club_key))

    positions = f[:position] && positions(f[:position])
    min = Text.to_int(f[:min_overall])
    max_age = Text.to_int(f[:max_age])
    br_keys = if f[:brazilian_clubs] in [true, "true"], do: brazilian_team_keys(data)

    list =
      Enum.filter(data.players, fn p ->
        (name == nil or name_match?(p.name, name)) and
          (nat == nil or Text.normalize(p.nationality) == nat) and
          (club == nil or (linked? and p.club_key == club_key) or
             (not linked? and p.club != nil and String.contains?(Text.normalize(p.club), club))) and
          (positions == nil or p.position in positions) and
          (min == nil or p.overall >= min) and
          (max_age == nil or p.age <= max_age) and
          (br_keys == nil or (p.club_key != nil and MapSet.member?(br_keys, p.club_key)))
      end)

    sorter =
      case to_string(f[:sort_by] || "overall") do
        "potential" -> &{-(&1.potential || 0), -(&1.overall || 0), &1.name}
        "age" -> &{&1.age || 0, -(&1.overall || 0), &1.name}
        "name" -> &{&1.name, 0, ""}
        _ -> &{-(&1.overall || 0), -(&1.potential || 0), &1.name}
      end

    {:ok, Enum.sort_by(list, sorter)}
  end

  defp name_match?(pname, tokens) do
    n = Text.normalize(pname)
    Enum.all?(tokens, &String.contains?(n, &1))
  end

  defp nationality(n) do
    case Text.normalize(n) do
      x when x in ["brazilian", "brasil", "brasileiro", "brazil", "br"] -> "brazil"
      "argentinian" -> "argentina"
      "argentine" -> "argentina"
      x -> x
    end
  end

  defp positions(p) do
    n = Text.normalize(p) |> String.trim_trailing("s")

    group =
      case n do
        x when x in ["forward", "attacker", "striker", "atacante"] -> "forward"
        x when x in ["midfielder", "midfield", "meia"] -> "midfielder"
        x when x in ["defender", "defence", "defense", "back", "zagueiro"] -> "defender"
        x when x in ["goalkeeper", "keeper", "goalie", "goleiro"] -> "goalkeeper"
        _ -> nil
      end

    if group, do: @position_groups[group], else: [String.upcase(String.trim(p))]
  end

  # Teams that play in Brazilian domestic competitions.
  defp brazilian_team_keys(data) do
    lib = List.last(Data.competitions())

    for m <- data.matches, m.competition != lib, k <- [m.home, m.away], into: MapSet.new(), do: k
  end

  @doc "Per-club summary of players at Brazilian clubs: `{club, count, avg_overall, best_player}`."
  def brazilian_club_summary(%Data{} = data, filters \\ []) do
    {:ok, ps} = players(data, filters |> Map.new() |> Map.put(:brazilian_clubs, true))

    ps
    |> Enum.group_by(& &1.club)
    |> Enum.map(fn {club, l} ->
      %{
        club: club,
        team: team_name(data, hd(l).club_key),
        players: length(l),
        avg_overall: Float.round(Enum.sum(Enum.map(l, & &1.overall)) / length(l), 1),
        best: Enum.max_by(l, & &1.overall)
      }
    end)
    |> Enum.sort_by(&{-&1.avg_overall, &1.club})
  end

  @doc "Cross-file profile: competitions/seasons played, overall record and FIFA squad."
  def team_profile(%Data{} = data, team) do
    with {:ok, stats} <- team_stats(data, team) do
      squad =
        data.players |> Enum.filter(&(&1.club_key == stats.key)) |> Enum.sort_by(&(-&1.overall))

      per_comp =
        stats.matches
        |> Enum.group_by(& &1.competition)
        |> Enum.map(fn {c, l} ->
          {c, l |> Enum.map(& &1.season) |> Enum.uniq() |> Enum.sort(), record(l, stats.key)}
        end)
        |> Enum.sort()

      {:ok,
       Map.merge(stats, %{
         state: data.teams[stats.key].state,
         competitions: per_comp,
         squad: squad
       })}
    end
  end

  @doc "Teams whose name contains `query` (all teams when nil), most matches first."
  def teams(%Data{teams: teams}, query \\ nil) do
    n = query && TeamNames.clean(query)

    teams
    |> Map.values()
    |> Enum.filter(
      &(n in [nil, ""] or String.contains?(&1.key, n) or
          String.contains?(TeamNames.clean(&1.name), n))
    )
    |> Enum.sort_by(&{-&1.matches, &1.name})
  end
end
