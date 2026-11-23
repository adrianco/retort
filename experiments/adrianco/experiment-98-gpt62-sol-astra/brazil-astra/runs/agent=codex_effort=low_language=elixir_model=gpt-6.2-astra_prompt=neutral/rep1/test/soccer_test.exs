defmodule SoccerTest do
  use ExUnit.Case
  alias Soccer.{Data, Query, Server}

  setup_all do
    %{db: Data.load()}
  end

  test "given all source files, source-scoped queries preserve every row", %{db: db} do
    for {file, count} <- [
          {"Brasileirao_Matches", 4180},
          {"Brazilian_Cup_Matches", 1337},
          {"Libertadores_Matches", 1255},
          {"novo_campeonato_brasileiro", 6886},
          {"BR-Football-Dataset", 10296}
        ] do
      r = Query.run(db, "matches", %{"source" => file})
      assert r.total == count
      assert Enum.all?(r.results, &(&1.source == file))
    end

    assert Query.run(db, "players", %{}).total == 18207
  end

  test "given overlapping seasons, league results count each fixture once", %{db: db} do
    a = %{"competition" => "Brasileirão", "season" => 2019}
    assert %{played: 380, average_goals: 2.31} = Query.run(db, "statistics", a)

    assert %{total: 20, results: [%{team: "flamengo", points: 90, played: 38, wins: 28}]} =
             Query.run(db, "standings", Map.put(a, "limit", 1))

    assert %{results: [%{rank: 17} | _]} =
             Query.run(db, "standings", Map.merge(a, %{"offset" => 16, "season" => 2020}))
  end

  test "when filtering a rivalry both venues contribute and the latest result comes first", %{
    db: db
  } do
    a = %{
      "team" => "Clube de Regatas do Flamengo",
      "opponent" => "Fluminense-RJ",
      "season" => 2019,
      "competition" => "Serie A"
    }

    assert %{total: 2, results: [later, earlier]} = Query.run(db, "matches", a)
    assert later.date > earlier.date
    assert earlier.home == later.away
    assert %{played: 2, wins: 1, draws: 1} = Query.run(db, "statistics", a)

    assert Query.run(
             db,
             "matches",
             Map.merge(a, %{"from" => later.date, "to" => later.date, "derby" => true})
           ).total == 1
  end

  test "when comparing home and away records, the splits reconcile", %{db: db} do
    a = %{
      "team" => "Sport Club Corinthians Paulista",
      "competition" => "Serie A",
      "season" => 2022
    }

    %{"home" => home, "away" => away} =
      Query.run(db, "statistics", Map.put(a, "group_by", "venue"))

    assert home.played == 19 and away.played == 19
    assert home == Query.run(db, "statistics", Map.put(a, "venue", "home"))
    assert away.goals_for + home.goals_for == Query.run(db, "statistics", a).goals_for

    assert %{"Libertadores" => _, "Serie A" => _} =
             Query.run(db, "statistics", %{"team" => "Palmeiras", "group_by" => "competition"})

    assert %{2018 => _, 2019 => _} =
             Query.run(db, "statistics", %{"team" => "Palmeiras", "group_by" => "season"})
  end

  test "when searching knockout stages, finals exclude preliminary rounds", %{db: db} do
    for season <- [2012, 2016, 2019] do
      assert Query.run(db, "matches", %{
               "competition" => "Copa do Brasil",
               "season" => season,
               "stage" => "final"
             }).total == 2
    end

    r =
      Query.run(db, "matches", %{
        "competition" => "Libertadores",
        "season" => 2018,
        "stage" => "quarterfinals"
      })

    assert r.total == 8
    assert Enum.all?(r.results, &(&1.stage == "quarterfinals"))
  end

  test "given FIFA snapshot, filters preserve positions, ratings and named attributes", %{db: db} do
    assert %{results: [%{"Name" => "Neymar Jr", "Overall" => "92", "Dribbling" => dribbling} | _]} =
             Query.run(db, "players", %{"nationality" => "Brazil"})

    assert String.to_integer(dribbling) > 90

    assert %{results: [%{"Name" => "L. Messi"}]} =
             Query.run(db, "players", %{"name" => "messi", "limit" => 1})

    p = Query.run(db, "team_profile", %{"team" => "Grêmio-RS", "season" => 2019})
    assert p.record.played > 0 and p.fifa_players.total > 0
    r = Query.run(db, "players", %{"club" => "Gremio", "position" => "forward"})
    assert r.total > 0 and Enum.all?(r.results, &(&1["Club"] == "Grêmio"))
  end

  test "when ranking goals, away records and winning margins the leaders are ordered", %{db: db} do
    for {filter, field} <- [
          {%{"rank_by" => "goals"}, :goals_for},
          {%{"venue" => "away", "rank_by" => "win_rate"}, :win_rate}
        ] do
      r =
        Query.run(
          db,
          "standings",
          Map.merge(filter, %{"competition" => "Serie A", "season" => 2019})
        )

      values = Enum.map(r.results, & &1[field])
      assert values == Enum.sort(values, :desc)
    end

    r = Query.run(db, "standings", %{"rank_by" => "margin"})
    margins = Enum.map(r.results, &abs(&1.home_goal - &1.away_goal))
    assert hd(margins) >= 8 and margins == Enum.sort(margins, :desc)
  end

  test "given missing scores, scheduled fixtures do not count as draws", %{db: db} do
    r = Query.run(db, "statistics", %{"source" => "Brasileirao_Matches", "season" => 2022})
    assert r.fixtures == 380 and r.played == 299
    assert Data.team("Atlético - MG") != Data.team("Atlético-GO")
    assert Data.date("29/03/2003") == "2003-03-29"
  end

  test "given a caller, MCP negotiates, lists tools, handles errors and returns parseable results",
       %{db: db} do
    rpc = fn method, params ->
      Server.process(JSON.encode!(%{jsonrpc: "2.0", id: 7, method: method, params: params}), db)
    end

    assert %{id: 7, result: %{protocolVersion: "2024-11-05"}} =
             rpc.("initialize", %{"protocolVersion" => "2024-11-05"})

    assert %{result: %{tools: tools}} = rpc.("tools/list", %{})
    assert length(tools) == 5
    assert Server.process(~s({"jsonrpc":"2.0","method":"notifications/initialized"}), db) == nil
    assert %{error: %{code: -32700}} = Server.process("{", db)
    assert %{error: %{code: -32601}} = rpc.("oops", %{})

    assert %{result: %{isError: true}} =
             rpc.("tools/call", %{"name" => "matches", "arguments" => %{"limit" => -1}})

    assert %{result: %{content: [%{text: text}]}} =
             rpc.("tools/call", %{
               "name" => "matches",
               "arguments" => %{"team" => "Palmeiras", "season" => 2023, "limit" => 1}
             })

    assert %{"results" => [%{"season" => 2023}]} = JSON.decode!(text)
  end
end
