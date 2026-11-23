defmodule Soccer.Query do
  alias Soccer.Data

  @derbies [
    ["flamengo", "fluminense"],
    ["corinthians", "palmeiras"],
    ["gremio", "internacional"],
    ["atletico-mg", "cruzeiro"],
    ["bahia", "vitoria"],
    ["flamengo", "vasco da gama"],
    ["corinthians", "sao paulo"],
    ["santos", "palmeiras"],
    ["santos", "sao paulo"],
    ["santos", "corinthians"],
    ["sao paulo", "palmeiras"],
    ["botafogo", "flamengo"],
    ["botafogo", "fluminense"],
    ["botafogo", "vasco da gama"],
    ["fluminense", "vasco da gama"],
    ["atletico-pr", "coritiba"],
    ["ceara", "fortaleza"],
    ["remo", "paysandu"],
    ["sport", "nautico"],
    ["sport", "santa cruz"],
    ["nautico", "santa cruz"]
  ]
  def run(db, "team_profile", %{"team" => team} = a) do
    filters = Map.take(a, ["team", "season", "competition"])

    %{
      team: Data.team(team),
      record: run(db, "statistics", filters),
      fixtures: run(db, "matches", Map.put(filters, "limit", 5)),
      fifa_players: run(db, "players", %{"club" => team, "limit" => 5})
    }
  end

  def run(db, "players", a) do
    club = key(a, "club")
    name = Data.fold(a["name"] || "")
    nation = Data.fold(a["nationality"] || "")

    rows =
      Enum.filter(db.players, fn p ->
        String.contains?(p.name, name) and (nation == "" or p.nationality == nation) and
          (is_nil(club) or String.contains?(p.club, club)) and
          position?(p.data["Position"], a["position"])
      end)

    page(rows, a, & &1.data)
  end

  def run(db, tool, a) do
    team = key(a, "team")
    opponent = key(a, "opponent")
    comp = competition(a["competition"])
    rows = if a["source"], do: db.raw, else: db.matches

    rows =
      Enum.filter(rows, fn m ->
        sides = [m.home, m.away]

        (is_nil(team) or team in sides) and (is_nil(opponent) or opponent in sides) and
          (a["venue"] != "home" or is_nil(team) or m.home == team) and
          (a["venue"] != "away" or is_nil(team) or m.away == team) and
          (is_nil(comp) or comp == m.competition) and
          (is_nil(a["season"]) or a["season"] == m.season) and
          (is_nil(a["source"]) or a["source"] == m.source) and
          (is_nil(a["stage"]) or a["stage"] in [m.stage, m.round]) and
          (is_nil(a["from"]) or (m.date != "NA" and m.date >= a["from"])) and
          (is_nil(a["to"]) or m.date <= a["to"]) and
          (a["derby"] != true or Enum.any?(@derbies, &(m.home in &1 and m.away in &1)))
      end)

    case tool do
      "matches" ->
        page(
          Enum.sort_by(rows, &{&1.date != "NA", &1.date, &1.home, &1.away}, :desc),
          a,
          &Function.identity/1
        )

      "statistics" ->
        statistics(rows, a, team)

      "standings" ->
        standings(rows, a, team)
    end
  end

  defp key(a, k), do: if(a[k], do: Data.team(a[k]))
  defp competition(nil), do: nil

  defp competition(s) do
    case Data.fold(s) do
      x when x in ["brasileirao", "serie a", "brasileirao serie a"] ->
        "Serie A"

      x when x in ["copa libertadores", "copa libertadores da america"] ->
        "Libertadores"

      x ->
        Enum.find(
          ["Serie B", "Serie C", "Copa do Brasil", "Libertadores"],
          x,
          &(Data.fold(&1) == x)
        )
    end
  end

  defp position?(p, "forward"), do: p in ~w(ST CF LW RW LF RF LS RS)
  defp position?(_p, nil), do: true
  defp position?(p, q), do: p == String.upcase(q)

  defp page(rows, a, format) do
    %{
      total: length(rows),
      offset: a["offset"] || 0,
      results: Enum.slice(rows, a["offset"] || 0, a["limit"] || 20) |> Enum.map(format)
    }
  end

  defp played?(m), do: is_integer(m.home_goal) and is_integer(m.away_goal)

  defp statistics(rows, a, team) do
    case a["group_by"] do
      nil ->
        summary(rows, team)

      "venue" when is_nil(team) ->
        raise ArgumentError, "venue grouping requires team"

      group ->
        rows
        |> Enum.group_by(fn m ->
          case group do
            "season" -> m.season
            "competition" -> m.competition
            "venue" -> if m.home == team, do: "home", else: "away"
          end
        end)
        |> Map.new(fn {k, ms} -> {k, summary(ms, team)} end)
    end
  end

  defp summary(rows, team) do
    played = Enum.filter(rows, &played?/1)

    scores =
      Enum.map(played, fn m ->
        if team == m.away, do: {m.away_goal, m.home_goal}, else: {m.home_goal, m.away_goal}
      end)

    record = record(scores)

    basic = %{
      fixtures: length(rows),
      played: length(played),
      average_goals: rate(record.goals_for + record.goals_against, record.played),
      home_win_rate: rate(100 * Enum.count(played, &(&1.home_goal > &1.away_goal)), record.played)
    }

    if team, do: Map.merge(basic, record), else: basic
  end

  defp record(scores) do
    w = Enum.count(scores, fn {f, a} -> f > a end)
    d = Enum.count(scores, fn {f, a} -> f == a end)
    gf = Enum.sum_by(scores, &elem(&1, 0))
    ga = Enum.sum_by(scores, &elem(&1, 1))
    n = length(scores)

    %{
      played: n,
      wins: w,
      draws: d,
      losses: n - w - d,
      goals_for: gf,
      goals_against: ga,
      goal_difference: gf - ga,
      points: 3 * w + d,
      win_rate: rate(100 * w, n)
    }
  end

  defp rate(_, 0), do: nil
  defp rate(v, n), do: Float.round(v / n, 2)

  defp standings(rows, a, team) do
    played = Enum.filter(rows, &played?/1)

    if a["rank_by"] == "margin" do
      played
      |> Enum.reject(&(&1.home_goal == &1.away_goal))
      |> Enum.sort_by(&{-abs(&1.home_goal - &1.away_goal), &1.date, &1.home})
      |> page(a, &Function.identity/1)
    else
      entries =
        for m <- played,
            {name, f, c, v} <- [
              {m.home, m.home_goal, m.away_goal, "home"},
              {m.away, m.away_goal, m.home_goal, "away"}
            ],
            is_nil(team) or name == team,
            is_nil(a["venue"]) or a["venue"] == v,
            do: {name, {f, c}}

      entries
      |> Enum.group_by(&elem(&1, 0), &elem(&1, 1))
      |> Enum.map(fn {name, scores} -> Map.put(record(scores), :team, name) end)
      |> Enum.sort_by(fn r ->
        metric =
          case a["rank_by"] do
            "goals" -> r.goals_for
            "win_rate" -> r.wins / r.played
            _ -> r.points
          end

        {-metric, -r.wins, -r.goal_difference, -r.goals_for, r.team}
      end)
      |> Enum.with_index(1)
      |> Enum.map(fn {r, i} -> Map.put(r, :rank, i) end)
      |> page(a, &Function.identity/1)
    end
  end
end
