defmodule SoccerMcp.QueryTest do
  # Feature: match, team, competition, player and statistics queries
  use ExUnit.Case, async: true

  import ExUnit.CaptureIO

  alias SoccerMcp.{Query, Store}

  @fixtures Path.expand("../fixtures", __DIR__)

  setup_all do
    capture_io(:stderr, fn -> send(self(), {:store, Store.load(@fixtures)}) end)
    assert_received {:store, store}
    {:ok, store: store}
  end

  describe "Feature: match queries" do
    test "Scenario: find matches between two teams", %{store: store} do
      # Given the match data is loaded
      # When I search for matches between "Flamengo" and "Fluminense"
      matches = Query.head_to_head(store, "Flamengo", "Fluminense")

      # Then I receive the matches, each with date, scores and competition
      assert length(matches) == 2
      assert Enum.all?(matches, &(&1.date && &1.home_goals && &1.competition))
      # And the most recent comes first
      assert hd(matches).date == ~D[2019-09-08]
    end

    test "Scenario: matches for one team in one season and competition", %{store: store} do
      # Given Flamengo played 3 Brasileirão matches in 2019 (4 including the Libertadores final)
      # When I search by team, competition and season
      matches =
        Query.find_matches(store,
          team: "Flamengo",
          competition: "Brasileirão Série A",
          season: 2019
        )

      # Then only those 3 come back
      assert length(matches) == 3
    end

    test "Scenario: home-only and date-range filters", %{store: store} do
      # Given Flamengo's 2019 Brasileirão matches
      # When I ask for home games only
      home =
        Query.find_matches(store,
          team: "Flamengo",
          venue: :home,
          season: 2019,
          competition: "Brasileirão Série A"
        )

      # Then two home games are returned
      assert length(home) == 2

      # And a date window of 1-9 June 2019 returns the three league games in that window
      window = Query.find_matches(store, from: ~D[2019-06-01], to: ~D[2019-06-09])
      assert length(window) == 3
    end

    test "Scenario: finals are found by stage, not semifinals", %{store: store} do
      # Given Copa do Brasil and Libertadores finals are in the data
      # When I search for the stage "final" in the cup
      cup_finals = Query.find_matches(store, competition: "Copa do Brasil", stage: "final")

      # Then both 2013 legs and the 2021 round-8 match are returned
      assert length(cup_finals) == 3

      # And the Libertadores final is returned when no competition is given
      assert Enum.any?(
               Query.find_matches(store, stage: "final"),
               &(&1.competition == "Copa Libertadores")
             )
    end
  end

  describe "Feature: clubs that share a short name" do
    test "Scenario: a state in the query picks the right club", %{store: store} do
      # Given Atlético-MG beat Flamengo 1-0 and Atlético-GO drew 2-2 in 2018
      # When I ask for Atlético-GO's matches
      go = Query.find_matches(store, team: "Atletico-GO", season: 2018)

      # Then only the Goiás match is returned
      assert [%{home_state: "go", home_goals: 2, away_goals: 2}] = go

      # And an unqualified name returns both clubs
      assert length(Query.find_matches(store, team: "Atletico", season: 2018)) == 2
    end

    test "Scenario: the table labels same-named clubs with their state", %{store: store} do
      # Given both Atlético clubs in the 2018 table
      table =
        Query.standings(
          Query.find_matches(store, competition: "Brasileirão Série A", season: 2018)
        )

      # When I read the team names
      names = Enum.map(table, & &1.team)

      # Then each Atlético is tagged with its state
      assert "Atletico (MG)" in names
      assert "Atletico (GO)" in names
    end
  end

  describe "Feature: team records" do
    test "Scenario: Flamengo's 2019 record", %{store: store} do
      # Given Flamengo's 2019 Brasileirão matches
      matches =
        Query.find_matches(store,
          team: "Flamengo",
          competition: "Brasileirão Série A",
          season: 2019
        )

      # When I calculate the record
      rec = Query.record(matches, "flamengo")

      # Then the wins, draws, losses, goals and win rate are correct
      assert rec.played == 3
      assert {rec.wins, rec.draws, rec.losses} == {2, 1, 0}
      assert {rec.goals_for, rec.goals_against} == {6, 2}
      assert rec.win_rate == 66.7
      assert rec.points == 7
    end
  end

  describe "Feature: head-to-head comparison" do
    test "Scenario: compare two teams head to head", %{store: store} do
      # Given Flamengo and Fluminense met twice in the dataset
      matches = Query.head_to_head(store, "Flamengo", "Fluminense")

      # When I compare them
      rec = Query.record(matches, "flamengo")

      # Then Flamengo has 1 win and 1 draw, and Fluminense has no wins
      assert {rec.wins, rec.draws, rec.losses} == {1, 1, 0}
    end
  end

  describe "Feature: competition standings" do
    test "Scenario: the 2019 table is calculated from results", %{store: store} do
      # Given the 2019 Brasileirão results
      matches = Query.find_matches(store, competition: "Brasileirão Série A", season: 2019)

      # When I calculate the standings
      table = Query.standings(matches)

      # Then teams are ordered by points, then goal difference, then goals scored
      assert Enum.map(table, &{&1.team, &1.points}) == [
               {"Flamengo", 7},
               {"Palmeiras", 4},
               {"Santos", 3},
               {"Corinthians", 1},
               {"Fluminense", 1}
             ]
    end
  end

  describe "Feature: statistical analysis" do
    test "Scenario: average goals and home win rate", %{store: store} do
      # Given the 2019 Brasileirão matches
      matches = Query.find_matches(store, competition: "Brasileirão Série A", season: 2019)

      # When I calculate the averages
      stats = Query.averages(matches)

      # Then goals per match, home wins, draws and away wins are reported
      assert stats.matches == 6
      assert stats.goals_per_match == 2.67
      assert stats.home_win_rate == 66.7
      assert stats.draw_rate == 33.3
      assert stats.away_win_rate == 0.0
    end

    test "Scenario: biggest wins by margin", %{store: store} do
      # Given every match in the fixtures
      # When I ask for the biggest wins
      [first, second | _] = Query.biggest_wins(store.matches, 2)

      # Then the 9-1 win ranks above the 8-0 win (same margin, more goals)
      assert {first.home_goals, first.away_goals} == {9, 1}
      assert {second.home_goals, second.away_goals} == {8, 0}
    end

    test "Scenario: best home record needs a minimum number of matches", %{store: store} do
      # Given only a few home matches per team in the fixtures
      # When I rank home records with a minimum of 1 match
      ranking = Query.venue_ranking(store.matches, :home, 1)

      # Then the top team has the best win rate
      assert hd(ranking).win_rate == 100.0

      # And a high minimum excludes every team
      assert Query.venue_ranking(store.matches, :home, 50) == []
    end
  end

  describe "Feature: player search" do
    test "Scenario: search by name ignores case and accents", %{store: store} do
      # Given the FIFA fixture contains "Gabriel Barbosa"
      # When I search for "gabriel"
      [player] = Query.players(store, name: "gabriel")

      # Then I receive that player
      assert player.name == "Gabriel Barbosa"
    end

    test "Scenario: filter Brazilian players at a minimum rating, best first", %{store: store} do
      # Given several Brazilian players in the fixture
      # When I filter by nationality and a minimum overall of 89
      players = Query.players(store, nationality: "brazil", min_overall: 89)

      # Then only players rated 89 or more come back, highest first
      assert Enum.map(players, & &1.name) == ["Neymar Jr", "Alisson"]
    end

    test "Scenario: filter by club and position", %{store: store} do
      # Given players at Paris Saint-Germain and goalkeepers
      assert Enum.map(Query.players(store, club: "paris"), & &1.name) == [
               "Neymar Jr",
               "Thiago Silva"
             ]

      assert Enum.map(Query.players(store, position: "gk"), & &1.name) == ["Alisson"]
    end
  end
end
