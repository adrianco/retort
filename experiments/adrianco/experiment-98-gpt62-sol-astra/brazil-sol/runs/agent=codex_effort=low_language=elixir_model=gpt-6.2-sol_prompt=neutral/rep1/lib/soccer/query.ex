defmodule Soccer.Query do
  @moduledoc "Queries matches, competition records and FIFA players through shared club identities."
  alias Soccer.{Data, Names}

  @derbies [
    ~w(flamengo fluminense),
    ~w(flamengo vasco),
    ~w(flamengo botafogo),
    ~w(fluminense vasco),
    ~w(fluminense botafogo),
    ~w(botafogo vasco),
    ~w(gremio internacional),
    ~w(cruzeiro atletico),
    ~w(athletico coritiba),
    ~w(palmeiras corinthians),
    ~w(palmeiras santos),
    ~w(corinthians santos),
    ["sao paulo", "corinthians"],
    ["sao paulo", "palmeiras"],
    ["sao paulo", "santos"],
    ~w(bahia vitoria),
    ~w(ceara fortaleza),
    ~w(sport nautico),
    ~w(sport santa),
    ~w(nautico santa),
    ~w(goias vila),
    ~w(remo paysandu),
    ~w(avai figueirense)
  ]
  @rival_names %{
    "vasco" => "vasco da gama",
    "atletico" => "atletico mg",
    "athletico" => "athletico pr",
    "santa" => "santa cruz",
    "vila" => "vila nova"
  }
  @rivals MapSet.new(@derbies, fn pair ->
            pair |> Enum.map(&Map.get(@rival_names, &1, &1)) |> Enum.sort()
          end)
  @forwards ~w(ST CF LF RF LS RS LW RW)
  @midfielders ~w(CAM CM CDM LM RM LAM RAM LCM RCM LDM RDM)
  @defenders ~w(CB LB RB LWB RWB LCB RCB)

  def matches(data, args) do
    fixtures = filter_matches(data, args)
    result = page(fixtures, args, &public_match/1, :matches)

    case {args["team"], args["opponent"]} do
      {team, opponent} when is_binary(team) and is_binary(opponent) ->
        Map.put(result, :head_to_head, [
          record_for(fixtures, team),
          record_for(fixtures, opponent)
        ])

      _ ->
        result
    end
  end

  def team(data, %{"team" => team} = args) do
    fixtures = filter_matches(data, args)
    {key, name} = Names.club(team)
    player_args = Map.take(args, ~w(limit offset)) |> Map.put("club", team)

    %{
      team: name,
      record: record(fixtures, key, name),
      by_competition: grouped_records(fixtures, & &1.competition, key, name, :competition),
      by_season: grouped_records(fixtures, & &1.season, key, name, :season),
      home: fixtures |> Enum.filter(&(&1.home_key == key)) |> record(key, name),
      away: fixtures |> Enum.filter(&(&1.away_key == key)) |> record(key, name),
      history: page(fixtures, args, &public_match/1, :matches),
      fifa_roster: players(data, player_args)
    }
  end

  def players(data, args) do
    name = args["name"] && Names.fold(args["name"])
    club = args["club"] && club_key(Names.club(args["club"]))
    nationality = args["nationality"] && nationality(args["nationality"])
    positions = args["position"] && positions(args["position"])
    minimum = args["min_overall"]
    domestic = args["brazilian_clubs"] == true

    players =
      data.players
      |> Enum.filter(fn p ->
        (!name || String.contains?(p.name_key, name)) &&
          (!club || p.club_key == club) &&
          (!nationality || p.nationality_key == nationality) &&
          (!positions || p.position in positions) &&
          (!minimum || (p.overall != nil && p.overall >= minimum)) &&
          (!domestic || MapSet.member?(data.clubs, p.club_key))
      end)
      |> Enum.sort_by(&{-(&1.overall || 0), &1.name_key, &1.id})

    fields = [:id, :name, :age, :nationality, :club, :position, :overall, :potential]

    render = fn player ->
      result = Map.take(player, fields)

      if args["attributes"] == true,
        do: Map.put(result, :attributes, player.attributes),
        else: result
    end

    result = page(players, args, render, :players)

    if domestic do
      clubs =
        players
        |> Enum.group_by(& &1.club_name)
        |> Enum.map(fn {name, roster} ->
          %{
            club: name,
            players: length(roster),
            average_overall: average(Enum.map(roster, & &1.overall))
          }
        end)
        |> Enum.sort_by(& &1.club)

      Map.put(result, :by_club, clubs)
    else
      result
    end
  end

  def competition(data, args) do
    fixtures = filter_matches(data, args)
    competition = Names.competition(args["competition"])
    season = args["season"]
    base = %{competition: competition, season: season}

    case args["view"] || "standings" do
      "results" ->
        Map.merge(base, page(fixtures, args, &public_match/1, :matches))

      "bracket" ->
        Map.put(base, :stages, stages(fixtures))

      "top_scorers" ->
        Map.put(
          base,
          :note,
          "The match files contain team scores only. Player goal totals cannot be determined."
        )

      view ->
        Map.merge(base, league_table(fixtures, competition, season, view))
    end
  end

  def statistics(data, args) do
    fixtures = filter_matches(data, args)
    scored = Enum.filter(fixtures, &scored?/1)

    case args["view"] || "summary" do
      "biggest_wins" ->
        scored
        |> Enum.reject(&(&1.home_goal == &1.away_goal))
        |> Enum.sort_by(&abs(&1.home_goal - &1.away_goal), :desc)
        |> page(
          args,
          fn m -> Map.put(public_match(m), :margin, abs(m.home_goal - m.away_goal)) end,
          :matches
        )

      "seasons" ->
        %{
          seasons:
            fixtures
            |> Enum.group_by(& &1.season)
            |> Enum.sort()
            |> Enum.map(fn {year, games} -> Map.put(summary(games), :season, year) end)
        }

      view when view in ["best_home", "best_away", "most_goals"] ->
        side = %{"best_home" => "home", "best_away" => "away"}[view]
        standings = team_records(scored, side)
        minimum = args["min_matches"] || 1

        standings =
          standings
          |> Enum.filter(&(&1.played >= minimum))
          |> Enum.sort_by(fn r ->
            if side,
              do: {-r.win_rate, -r.wins, -r.goal_difference, r.team},
              else: {-r.goals_for, -r.goal_difference, 0, r.team}
          end)

        page(standings, args, &Function.identity/1, :teams)

      "summary" ->
        summary(fixtures)
    end
  end

  defp filter_matches(data, args) do
    team = args["team"] && club_key(Names.club(args["team"]))
    opponent = args["opponent"] && club_key(Names.club(args["opponent"]))
    competition = args["competition"] && Names.competition(args["competition"])
    from = args["from"] && Data.date(args["from"])
    to = args["to"] && Data.date(args["to"])
    stage = args["stage"] && normalize_stage(args["stage"])
    season = args["season"]
    seasons = args["seasons"]
    round = args["round"]
    fixtures = if args["source"], do: Map.fetch!(data.sources, args["source"]), else: data.matches

    Enum.filter(fixtures, fn m ->
      team_matches?(m, team, args["venue"]) &&
        (!opponent || opponent_matches?(m, team, opponent)) &&
        (!competition || m.competition == competition) &&
        (!season || m.season == season) &&
        (!seasons || m.season in seasons) &&
        (!from || (m.date && m.date >= from)) &&
        (!to || (m.date && m.date <= to)) &&
        (!round || m.round == round) &&
        (!stage || m.stage == stage) &&
        (args["derbies"] != true || MapSet.member?(@rivals, Enum.sort([m.home_key, m.away_key])))
    end)
  end

  defp club_key({key, _}), do: key
  defp team_matches?(_, nil, _), do: true
  defp team_matches?(m, team, "home"), do: m.home_key == team
  defp team_matches?(m, team, "away"), do: m.away_key == team
  defp team_matches?(m, team, _), do: m.home_key == team or m.away_key == team

  defp opponent_matches?(m, team, opponent),
    do: {m.home_key, m.away_key} in [{team, opponent}, {opponent, team}]

  defp normalize_stage(stage) do
    case Names.fold(stage) do
      name when name in ["final", "finals"] -> "final"
      name when name in ["semifinal", "semi final", "semi finals"] -> "semifinals"
      name when name in ["quarterfinal", "quarter final", "quarter finals"] -> "quarterfinals"
      name -> name
    end
  end

  defp public_match(match), do: Map.drop(match, [:home_key, :away_key])

  defp page(items, args, render, key) do
    total = length(items)
    offset = args["offset"] || 0
    limit = args["limit"] || 20
    entries = items |> Enum.slice(offset, limit) |> Enum.map(render)
    next_offset = if offset + limit < total, do: offset + limit
    %{key => entries, total: total, offset: offset, next_offset: next_offset}
  end

  defp positions(value) do
    case Names.fold(value) do
      pos when pos in ["forward", "forwards", "attacker"] -> @forwards
      pos when pos in ["midfielder", "midfielders"] -> @midfielders
      pos when pos in ["defender", "defenders"] -> @defenders
      pos when pos in ["goalkeeper", "goalkeepers"] -> ["GK"]
      pos -> [String.upcase(pos)]
    end
  end

  defp nationality(value) do
    case Names.fold(value) do
      name when name in ["brazilian", "brasil"] -> "brazil"
      name -> name
    end
  end

  defp record_for(fixtures, team) do
    {key, name} = Names.club(team)
    record(fixtures, key, name)
  end

  defp record(fixtures, key, name) do
    fixtures
    |> Enum.filter(&scored?/1)
    |> Enum.map(fn m ->
      if m.home_key == key, do: {m.home_goal, m.away_goal}, else: {m.away_goal, m.home_goal}
    end)
    |> tally(name)
    |> Map.put(:fixtures, length(fixtures))
  end

  defp tally(scores, name) do
    {wins, draws, losses, goals, against} =
      Enum.reduce(scores, {0, 0, 0, 0, 0}, fn {f, a}, {w, d, l, gf, ga} ->
        {w + indicator(f > a), d + indicator(f == a), l + indicator(f < a), gf + f, ga + a}
      end)

    played = wins + draws + losses

    %{
      team: name,
      played: played,
      wins: wins,
      draws: draws,
      losses: losses,
      goals_for: goals,
      goals_against: against,
      goal_difference: goals - against,
      points: 3 * wins + draws,
      win_rate: percentage(wins, played)
    }
  end

  defp team_records(fixtures, side) do
    fixtures
    |> Enum.flat_map(fn m ->
      home = {m.home_key, m.home_team, {m.home_goal, m.away_goal}}
      away = {m.away_key, m.away_team, {m.away_goal, m.home_goal}}

      case side do
        "home" -> [home]
        "away" -> [away]
        _ -> [home, away]
      end
    end)
    |> Enum.group_by(&elem(&1, 0))
    |> Enum.map(fn {_, [{_, name, _} | _] = matches} ->
      tally(Enum.map(matches, &elem(&1, 2)), name)
    end)
  end

  defp grouped_records(fixtures, group, key, name, label) do
    fixtures
    |> Enum.group_by(group)
    |> Enum.sort()
    |> Enum.map(fn {value, games} -> Map.put(record(games, key, name), label, value) end)
  end

  defp stages(fixtures) do
    order = ["group stage", "round of 16", "quarterfinals", "semifinals", "final"]

    fixtures
    |> Enum.group_by(&(&1.stage || if(&1.round, do: "Round #{&1.round}", else: "Unspecified")))
    |> Enum.sort_by(fn {stage, games} ->
      {Enum.find_index(order, &(&1 == stage)) || -1, hd(games).round || 0}
    end)
    |> Enum.map(fn {stage, games} ->
      %{stage: stage, matches: Enum.map(Enum.reverse(games), &public_match/1)}
    end)
  end

  defp league_table(fixtures, "Brasileirão Série A", season, view) do
    standings = fixtures |> Enum.filter(&scored?/1) |> team_records(nil) |> rank()
    teams = if season in [2003, 2004], do: 24, else: if(season == 2005, do: 22, else: 20)

    complete =
      length(standings) == teams and Enum.all?(standings, &(&1.played == (teams - 1) * 2))

    note =
      "Calculated from recorded scores using points, wins, goal difference and goals scored. Administrative adjustments and additional tie-break rules are outside the match data."

    case view do
      "standings" ->
        %{standings: standings, complete: complete, note: note}

      "champion" ->
        %{champion: if(complete, do: List.first(standings)), complete: complete, note: note}

      "relegation" when season >= 2006 ->
        %{
          relegated: if(complete, do: Enum.take(standings, -4), else: []),
          complete: complete,
          note: note
        }

      "relegation" ->
        count = if season in [2004, 2005], do: 4, else: 2

        %{
          relegated: if(complete, do: Enum.take(standings, -count), else: []),
          complete: complete,
          note: note
        }
    end
  end

  defp league_table(fixtures, "Brasileirão Série B", _, "standings") do
    standings = fixtures |> Enum.filter(&scored?/1) |> team_records(nil) |> rank()

    %{
      standings: standings,
      complete: length(standings) == 20 and Enum.all?(standings, &(&1.played == 38)),
      note:
        "Calculated from recorded scores. Administrative adjustments and additional tie-break rules are outside the match data."
    }
  end

  defp league_table(_, _, _, _),
    do: %{
      note:
        "This competition view requires a supported league format. Use results or bracket for the recorded fixtures."
    }

  defp rank(records) do
    records
    |> Enum.sort_by(&{-&1.points, -&1.wins, -&1.goal_difference, -&1.goals_for, &1.team})
    |> Enum.with_index(1)
    |> Enum.map(fn {record, rank} -> Map.put(record, :rank, rank) end)
  end

  defp summary(fixtures) do
    scored = Enum.filter(fixtures, &scored?/1)
    played = length(scored)
    home_wins = Enum.count(scored, &(&1.home_goal > &1.away_goal))
    away_wins = Enum.count(scored, &(&1.home_goal < &1.away_goal))

    %{
      fixtures: length(fixtures),
      played: played,
      average_goals: average(Enum.map(scored, &(&1.home_goal + &1.away_goal))),
      home_wins: home_wins,
      away_wins: away_wins,
      draws: played - home_wins - away_wins,
      home_win_rate: percentage(home_wins, played),
      away_win_rate: percentage(away_wins, played)
    }
  end

  defp scored?(m), do: is_integer(m.home_goal) and is_integer(m.away_goal)
  defp indicator(true), do: 1
  defp indicator(false), do: 0
  defp average([]), do: nil
  defp average(values), do: Float.round(Enum.sum(values) / length(values), 2)
  defp percentage(_, 0), do: nil
  defp percentage(n, total), do: Float.round(100 * n / total, 2)
end
