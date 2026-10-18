defmodule SoccerMcp.RealDataTest do
  # Feature: the provided Kaggle datasets are fully loadable and queryable
  #   These tests use the real files in data/kaggle and check the success
  #   criteria from the specification.
  use ExUnit.Case, async: true

  import ExUnit.CaptureIO

  alias SoccerMcp.{Query, Store, Tools}

  @data_dir Path.expand("../../data/kaggle", __DIR__)

  setup_all do
    capture_io(:stderr, fn -> send(self(), {:store, Store.load(@data_dir)}) end)
    assert_received {:store, store}
    {:ok, store: store}
  end

  describe "Feature: data coverage" do
    test "Scenario: all six files load", %{store: store} do
      # Given the provided data directory
      # Then all six files are present in the load summary with records
      assert length(store.sources) == 6
      assert Enum.all?(store.sources, fn {_file, count} -> count > 0 end)
      assert length(store.players) > 18_000
      assert length(store.matches) > 17_000
    end

    test "Scenario: the 2019 Brasileirão has 380 matches and Flamengo wins it", %{store: store} do
      # Given the full 2019 league results (20 clubs, 38 rounds, each match once)
      matches = Query.find_matches(store, competition: "Brasileirão Série A", season: 2019)

      # Then there are 380 matches, no duplicates from overlapping files
      assert length(matches) == 380

      # And the table matches the specification's example: Flamengo 90 pts (28W, 6D, 4L)
      [champion | _] = Query.standings(matches)

      assert {champion.team, champion.points, champion.wins, champion.draws, champion.losses} ==
               {"Flamengo", 90, 28, 6, 4}
    end

    test "Scenario: the aggregate query meets the 5 second budget", %{store: store} do
      # Given the full match data
      # When I compute league averages and the standings
      {micros, _} =
        :timer.tc(fn ->
          Query.averages(Query.find_matches(store, competition: "Brasileirão Série A"))

          Query.standings(
            Query.find_matches(store, competition: "Brasileirão Série A", season: 2019)
          )
        end)

      # Then it finishes well inside the budget
      assert micros < 5_000_000
    end
  end

  describe "Feature: sample questions from the specification" do
    @questions [
      {"search_matches", %{"team" => "Flamengo", "opponent" => "Fluminense"}},
      {"search_matches", %{"team" => "Palmeiras", "season" => 2023}},
      {"search_matches", %{"competition" => "Copa do Brasil", "stage" => "final"}},
      {"search_matches", %{"team" => "Flamengo", "opponent" => "Corinthians", "limit" => 1}},
      {"team_stats",
       %{
         "team" => "Corinthians",
         "competition" => "Brasileirão",
         "season" => 2022,
         "venue" => "home"
       }},
      {"team_stats", %{"team" => "Palmeiras", "competition" => "Brasileirão", "season" => 2023}},
      {"head_to_head", %{"team_a" => "Palmeiras", "team_b" => "Santos"}},
      {"competition_standings", %{"competition" => "Brasileirão", "season" => 2019}},
      {"competition_standings", %{"competition" => "Brasileirão", "season" => 2020}},
      {"search_players", %{"nationality" => "Brazil", "min_overall" => 85}},
      {"search_players", %{"club" => "Paris", "limit" => 5}},
      {"search_players", %{"name" => "Gabriel Barbosa"}},
      {"search_players", %{"position" => "ST", "nationality" => "Brazil"}},
      {"match_statistics", %{"kind" => "averages"}},
      {"match_statistics",
       %{"kind" => "averages", "competition" => "Libertadores", "season" => 2019}},
      {"match_statistics", %{"kind" => "biggest_wins", "limit" => 5}},
      {"match_statistics", %{"kind" => "best_home", "competition" => "Brasileirão"}},
      {"match_statistics", %{"kind" => "best_away", "competition" => "Brasileirão"}},
      {"search_matches",
       %{"team" => "Flamengo", "competition" => "Libertadores", "season" => 2019}},
      {"search_matches",
       %{"competition" => "Copa do Brasil", "season" => 2013, "stage" => "final"}}
    ]

    test "Scenario: at least 20 sample questions are answered", %{store: store} do
      # Given twenty questions covering matches, teams, players, competitions and statistics
      # When each is sent to the tools
      results =
        Enum.map(@questions, fn {tool, args} -> {tool, args, Tools.call(tool, args, store)} end)

      # Then every one returns an answer, not an error, within the budget
      for {tool, args, result} <- results do
        assert {:ok, text} = result, "#{tool} #{inspect(args)} failed: #{inspect(result)}"
        assert is_binary(text) and text != ""
      end

      assert length(results) >= 20
    end

    test "Scenario: Copa do Brasil finals are found across seasons", %{store: store} do
      # Given the cup data with round 8 as the final
      # When I search for finals
      {:ok, text} =
        Tools.call(
          "search_matches",
          %{"competition" => "Copa do Brasil", "stage" => "final", "limit" => 100},
          store
        )

      # Then finals from several seasons are returned
      assert text =~ "Copa do Brasil, final"
      assert text =~ "2013)"
    end
  end
end
