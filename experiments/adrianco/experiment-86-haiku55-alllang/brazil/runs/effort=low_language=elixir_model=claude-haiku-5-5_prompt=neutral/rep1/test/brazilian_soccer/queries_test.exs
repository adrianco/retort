defmodule BrazilianSoccer.QueriesTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.{Data, Queries}

  @fixtures Path.expand("../fixtures/kaggle", __DIR__)

  setup_all do
    %{data: Data.load(@fixtures)}
  end

  describe "Scenario: find matches between two teams" do
    test "Given Flamengo and Fluminense, then their meetings are listed newest first", %{data: d} do
      result = Queries.find_matches(d.matches, team: "Flamengo", opponent: "Fluminense")

      assert result.total == 2
      assert Enum.map(result.matches, & &1.date) == [~D[2023-09-03], ~D[2023-05-28]]
    end

    test "Given a team with a side filter, then only home matches are returned", %{data: d} do
      result = Queries.find_matches(d.matches, team: "Flamengo", side: :home, season: 2023)

      assert Enum.map(result.matches, & &1.home) == ["Flamengo", "Flamengo"]
    end

    test "Given a derby flag, then only traditional rivalries match", %{data: d} do
      result = Queries.find_matches(d.matches, derby: true)

      assert result.total == 4

      assert Enum.all?(
               result.matches,
               &(&1.home_key in ["flamengo", "fluminense", "corinthians", "palmeiras"])
             )
    end

    test "Given a limit, then the total is still reported", %{data: d} do
      result = Queries.find_matches(d.matches, season: 2022, limit: 2)

      assert result.total == 4
      assert length(result.matches) == 2
    end
  end

  describe "Scenario: filter by competition, season and date range" do
    test "Given a competition name in any spelling, then only that competition matches", %{
      data: d
    } do
      assert Queries.find_matches(d.matches, competition: "libertadores").total == 2
      assert Queries.find_matches(d.matches, competition: "Copa do Brasil").total == 4
    end

    test "Given a date range, then matches outside it are excluded", %{data: d} do
      result = Queries.find_matches(d.matches, date_from: ~D[2023-06-01], date_to: ~D[2023-12-31])
      assert result.total == 4
    end
  end

  describe "Scenario: team record" do
    test "Given Corinthians in 2022, then wins, draws, losses and goals are counted", %{data: d} do
      r =
        Queries.team_record(d.matches, "Corinthians",
          season: 2022,
          competition: "Brasileirão Série A"
        )

      assert r.team == "Corinthians"
      assert r.played == 3
      assert {r.wins, r.draws, r.losses} == {1, 1, 1}
      assert {r.goals_for, r.goals_against} == {3, 4}
      assert r.win_rate == 33.3
    end

    test "Given Corinthians home matches in 2022, then the home record is separate", %{data: d} do
      r = Queries.team_record(d.matches, "Corinthians", season: 2022, side: :home)

      assert r.played == 2
      assert r.win_rate == 50.0
    end

    test "Given a team with no matches, then the record is zero", %{data: d} do
      r = Queries.team_record(d.matches, "Vasco", season: 2023)
      assert r.played == 0
      assert r.win_rate == 0.0
    end
  end

  describe "Scenario: head to head" do
    test "Given Flamengo and Fluminense, then the series score is reported", %{data: d} do
      h2h = Queries.head_to_head(d.matches, "Flamengo", "Fluminense")

      assert h2h.played == 2
      assert {h2h.wins_a, h2h.wins_b, h2h.draws} == {1, 1, 0}
      assert {h2h.goals_a, h2h.goals_b} == {2, 2}
      assert hd(h2h.matches).date == ~D[2023-09-03]
    end

    test "Given the spelling variant São Paulo, then it resolves to the same team", %{data: d} do
      h2h = Queries.head_to_head(d.matches, "São Paulo", "Flamengo")
      assert h2h.played == 1
      assert h2h.draws == 1
    end
  end

  describe "Scenario: league standings calculated from results" do
    test "Given the 2022 Brasileirão, then the table is ordered by points", %{data: d} do
      table = Queries.standings(d.matches, season: 2022)

      assert Enum.map(table, &{&1.team, &1.points}) == [
               {"Palmeiras", 7},
               {"Corinthians", 4},
               {"Santos", 0}
             ]

      [palmeiras | _] = table
      assert {palmeiras.wins, palmeiras.draws, palmeiras.losses} == {2, 1, 0}
    end

    test "Given equal points, then goal difference breaks the tie, then name", %{data: d} do
      table = Queries.standings(d.matches, season: 2023)

      assert Enum.map(table, & &1.team) == ["Flamengo", "Fluminense"]
      assert Enum.all?(table, &(&1.points == 3))
    end

    test "Given the Copa do Brasil, then it is excluded from the Série A table by default", %{
      data: d
    } do
      table = Queries.standings(d.matches, season: 2023)
      refute Enum.any?(table, &(&1.team == "Copa do Brasil"))
      refute Enum.any?(table, &(&1.team == "Santos"))
    end
  end

  describe "Scenario: aggregate statistics" do
    test "Given the 2022 Brasileirão, then goals per match and home/away rates are computed", %{
      data: d
    } do
      stats = Queries.league_stats(d.matches, season: 2022, competition: "Brasileirão Série A")

      assert stats.matches == 4
      assert stats.total_goals == 11
      assert stats.avg_goals_per_match == 2.75
      assert stats.home_win_rate == 50.0
      assert stats.away_win_rate == 25.0
      assert stats.draw_rate == 25.0
    end

    test "Given a season with no matches, then the stats are zero rather than an error", %{
      data: d
    } do
      stats = Queries.league_stats(d.matches, season: 1990)
      assert stats.matches == 0
      assert stats.avg_goals_per_match == 0.0
    end

    test "Given the 2022 Brasileirão, then the biggest wins come first", %{data: d} do
      wins = Queries.biggest_wins(d.matches, season: 2022, limit: 2)

      assert Enum.map(wins, &{&1.home, &1.away}) == [
               {"Santos", "Palmeiras"},
               {"Palmeiras", "Corinthians"}
             ]
    end
  end

  describe "Scenario: team rankings" do
    test "Given home win rate with a minimum of one match, then the best home teams lead", %{
      data: d
    } do
      rows =
        Queries.ranking(d.matches, "home_win_rate",
          competition: "Brasileirão Série A",
          min_matches: 1
        )

      assert Enum.take(rows, 3) |> Enum.map(& &1.value) == [100.0, 100.0, 100.0]
      assert %{team: "Corinthians", value: 50.0} = Enum.find(rows, &(&1.team == "Corinthians"))
      assert List.last(rows).team == "Santos"
      assert List.last(rows).value == 0.0
    end

    test "Given the default minimum of ten matches, then no team qualifies in the small fixture",
         %{data: d} do
      assert Queries.ranking(d.matches, "points") == []
    end

    test "Given an unknown metric, then it raises" do
      assert_raise KeyError, fn -> Queries.ranking([], "shots") end
    end
  end

  describe "Scenario: player search" do
    test "Given a player's name, then the search is accent and case insensitive", %{data: d} do
      %{players: [p], total: 1} = Queries.search_players(d.players, name: "gabriel BARBOSA")
      assert p.club == "CR Flamengo"
    end

    test "Given Brazil, then all Brazilian players are returned best first", %{data: d} do
      result = Queries.search_players(d.players, nationality: "Brazil")

      assert result.total == 4

      assert Enum.map(result.players, & &1.name) == [
               "Neymar Jr",
               "Alisson",
               "Gabriel Barbosa",
               "Rodrigo Caio"
             ]
    end

    test "Given a club substring, then Flamengo players match", %{data: d} do
      result = Queries.search_players(d.players, club: "Flamengo")
      assert Enum.map(result.players, & &1.name) == ["Gabriel Barbosa", "Pedro Ruiz"]
    end

    test "Given a position group, then forwards are matched by their codes", %{data: d} do
      result = Queries.search_players(d.players, position: "forwards")

      assert Enum.map(result.players, & &1.name) == [
               "L. Messi",
               "Cristiano Ronaldo",
               "Neymar Jr",
               "Gabriel Barbosa"
             ]
    end

    test "Given a minimum rating, then weaker players are excluded", %{data: d} do
      assert Queries.search_players(d.players, min_overall: 90).total == 3
    end

    test "Given a position code, then only that code matches", %{data: d} do
      assert [%{name: "Alisson"}] = Queries.search_players(d.players, position: "gk").players
    end
  end
end
