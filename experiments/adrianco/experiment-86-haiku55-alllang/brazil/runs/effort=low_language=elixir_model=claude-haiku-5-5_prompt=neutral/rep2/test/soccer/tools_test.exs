defmodule SoccerMcp.ToolsTest do
  # Feature: the MCP tools answer natural language questions in the spec's formats
  use ExUnit.Case, async: true

  import ExUnit.CaptureIO

  alias SoccerMcp.{Store, Tools}

  @fixtures Path.expand("../fixtures", __DIR__)

  setup_all do
    capture_io(:stderr, fn -> send(self(), {:store, Store.load(@fixtures)}) end)
    assert_received {:store, store}
    {:ok, store: store}
  end

  describe "Feature: tool catalogue" do
    test "Scenario: every tool has a name, description and schema" do
      # Given the tool definitions
      # When I list them
      names = Enum.map(Tools.definitions(), & &1.name)

      # Then the six tools from the specification are present
      assert Enum.sort(names) ==
               Enum.sort([
                 "search_matches",
                 "team_stats",
                 "head_to_head",
                 "competition_standings",
                 "search_players",
                 "match_statistics"
               ])

      assert Enum.all?(
               Tools.definitions(),
               &(is_binary(&1.description) and is_map(&1.inputSchema))
             )
    end
  end

  describe "Feature: match answers" do
    test "Scenario: a head-to-head question gets a summary and the matches", %{store: store} do
      # Given Flamengo and Fluminense in the data
      # When I ask for matches between them
      assert {:ok, text} =
               Tools.call(
                 "search_matches",
                 %{"team" => "Flamengo", "opponent" => "Fluminense"},
                 store
               )

      # Then the answer has the head-to-head line and dated scores
      assert text =~ "Head-to-head in dataset: Flamengo 1 wins, Fluminense 0 wins, 1 draws"
      assert text =~ "2019-05-28: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 8, 2019)"
    end

    test "Scenario: a question with no matches says so", %{store: store} do
      # Given no Copa Libertadores matches for Palmeiras in the fixtures
      # When I ask for them
      assert {:ok, "No matches found in the dataset."} =
               Tools.call(
                 "search_matches",
                 %{"team" => "Palmeiras", "competition" => "Libertadores"},
                 store
               )
    end

    test "Scenario: team statistics for a season with a venue", %{store: store} do
      # Given Flamengo's 2019 home games in the league
      # When I ask for the record
      assert {:ok, text} =
               Tools.call(
                 "team_stats",
                 %{
                   "team" => "Flamengo",
                   "competition" => "Brasileirão",
                   "season" => 2019,
                   "venue" => "home"
                 },
                 store
               )

      # Then wins, goals and win rate are listed
      assert text =~ "Matches: 2"
      assert text =~ "Wins: 2, Draws: 0, Losses: 0"
      assert text =~ "Goals For: 6, Goals Against: 2"
      assert text =~ "Win rate: 100.0%"
    end

    test "Scenario: the league table answers with a ranked list", %{store: store} do
      # Given the 2019 league results
      # When I ask for the standings
      assert {:ok, text} =
               Tools.call(
                 "competition_standings",
                 %{"competition" => "Brasileirão", "season" => 2019},
                 store
               )

      # Then the champion is listed first with points and records
      assert text =~ "1. Flamengo - 7 pts (2W, 1D, 0L)"
    end

    test "Scenario: season arrives as a number or a string", %{store: store} do
      # Given the same question with the year as an integer and as text
      {:ok, as_int} =
        Tools.call(
          "competition_standings",
          %{"competition" => "Brasileirão", "season" => 2019},
          store
        )

      {:ok, as_text} =
        Tools.call(
          "competition_standings",
          %{"competition" => "Brasileirão", "season" => "2019"},
          store
        )

      # Then both give the same table
      assert as_int == as_text
    end
  end

  describe "Feature: statistics and players" do
    test "Scenario: average goals per match", %{store: store} do
      # Given the 2019 league
      assert {:ok, text} =
               Tools.call(
                 "match_statistics",
                 %{"kind" => "averages", "competition" => "Brasileirão", "season" => 2019},
                 store
               )

      # Then the averages are reported
      assert text =~ "Average goals per match: 2.67"
    end

    test "Scenario: biggest wins", %{store: store} do
      # Given the fixture matches
      assert {:ok, text} =
               Tools.call("match_statistics", %{"kind" => "biggest_wins", "limit" => 2}, store)

      # Then the largest margin is listed first
      assert text =~ "1. 2021-06-08: São Paulo 9-1 4 de Julho EC"
    end

    test "Scenario: find a player by name", %{store: store} do
      # Given the FIFA fixture
      assert {:ok, text} = Tools.call("search_players", %{"name" => "Gabriel Barbosa"}, store)

      # Then the player's rating and club are listed
      assert text =~ "Gabriel Barbosa - Overall: 80, Position: ST, Club: Internacional"
    end

    test "Scenario: a player search needs at least one filter", %{store: store} do
      # Given a search with only a limit
      # When I call the tool
      # Then the tool explains what is missing
      assert {:error, msg} = Tools.call("search_players", %{"limit" => 5}, store)
      assert msg =~ "at least one of"
    end
  end

  describe "Feature: bad requests get readable errors" do
    test "Scenario: missing required arguments", %{store: store} do
      # Given a team statistics request without a team
      # When I call the tool
      # Then the error names the missing argument
      assert {:error, "missing required argument team"} = Tools.call("team_stats", %{}, store)
    end

    test "Scenario: an unknown competition", %{store: store} do
      # Given a competition the dataset does not contain
      assert {:error, msg} =
               Tools.call("search_matches", %{"competition" => "Premier League"}, store)

      assert msg =~ "unknown competition"
    end

    test "Scenario: a malformed date", %{store: store} do
      # Given a date that is not in a supported format
      assert {:error, msg} = Tools.call("search_matches", %{"date_from" => "soon"}, store)
      assert msg =~ "date_from must be a date"
    end

    test "Scenario: the standings need a season", %{store: store} do
      # Given a standings request without a season
      assert {:error, "missing required argument season"} =
               Tools.call("competition_standings", %{"competition" => "Brasileirão"}, store)
    end

    test "Scenario: an unknown tool", %{store: store} do
      # Given a tool name that does not exist
      assert {:error, "unknown tool: weather"} = Tools.call("weather", %{}, store)
    end
  end
end
