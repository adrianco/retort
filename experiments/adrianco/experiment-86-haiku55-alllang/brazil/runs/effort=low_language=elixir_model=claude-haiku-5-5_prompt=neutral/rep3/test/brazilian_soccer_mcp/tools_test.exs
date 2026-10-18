defmodule BrazilianSoccerMcp.ToolsTest do
  use ExUnit.Case, async: true

  import BrazilianSoccerMcp.Fixtures

  alias BrazilianSoccerMcp.{Store, Tools}

  @data data()

  describe "Given the tool catalogue" do
    test "When listed Then every tool has a name, description and object schema" do
      tools = Tools.definitions()

      assert length(tools) == 10
      assert Enum.all?(tools, &(is_binary(&1.description) and &1.inputSchema.type == "object"))
    end

    test "When a required argument is missing Then the schema lists it as required" do
      team_record = Enum.find(Tools.definitions(), &(&1.name == "team_record"))

      assert team_record.inputSchema.required == ["team"]
    end
  end

  describe "Given a tool call with valid arguments" do
    test "When team_record is called Then the result is formatted as text" do
      {:ok, text} = Tools.call("team_record", %{"team" => "Alpha", "season" => 2023}, @data)

      assert text == """
             Alpha (2023):
             - Matches: 4
             - Wins: 2, Draws: 1, Losses: 1
             - Goals For: 7, Goals Against: 4
             - Win rate: 50.0%\
             """
    end

    test "When standings are called Then the champion is marked and points are shown" do
      {:ok, text} = Tools.call("standings", %{"season" => "2023"}, @data)

      assert text == """
             2023 Brasileirão Série A standings (calculated from matches):
             1. Gamma - 5 pts (1W, 2D, 0L) - Champion
             2. Alpha - 4 pts (1W, 1D, 1L)
             3. Beta - 1 pts (0W, 1D, 1L)\
             """
    end

    test "When search_matches is called with a venue Then the header states the venue scope" do
      {:ok, text} =
        Tools.call(
          "search_matches",
          %{"team" => "Alpha", "season" => 2023, "venue" => "home"},
          @data
        )

      assert String.starts_with?(text, "3 matches (showing 3, 2023, home matches only):")
      assert text =~ "- 2023-05-01: Alpha 4-0 Beta (Copa do Brasil, Round 1)"
    end

    test "When a round is numeric Then it is shown as a round number" do
      {:ok, text} = Tools.call("search_matches", %{"team" => "Beta", "season" => 2023}, @data)

      assert text =~ "(Brasileirão Série A, Round 1)"
    end

    test "When head_to_head is called Then the summary includes both sides' wins" do
      {:ok, text} = Tools.call("head_to_head", %{"team_a" => "Alpha", "team_b" => "Beta"}, @data)

      assert text =~ "- Alpha wins: 2, Beta wins: 0, Draws: 0"
      assert text =~ "- Goals: Alpha 6 - 1 Beta"
    end

    test "When players are searched Then each line shows overall, position and club" do
      {:ok, text} =
        Tools.call("search_players", %{"nationality" => "Brazil", "min_overall" => "80"}, @data)

      assert text == """
             Players (2):
             1. Ana Silva - Overall: 85, Position: ST, Club: Alpha
             2. Bruno Costa - Overall: 80, Position: CM, Club: Alpha\
             """
    end

    test "When no players match Then the result says so" do
      assert {:ok, "No players found."} =
               Tools.call("search_players", %{"name" => "Nobody"}, @data)
    end
  end

  describe "Given invalid arguments" do
    test "When a required argument is absent Then an error names it" do
      assert {:error, "Missing required argument: team"} = Tools.call("team_record", %{}, @data)
    end

    test "When a date is not ISO formatted Then an error explains the format" do
      assert {:error, "Dates must be YYYY-MM-DD, got: 01/03/2023"} =
               Tools.call("search_matches", %{"date_from" => "01/03/2023"}, @data)
    end

    test "When the venue is unknown Then an error lists the allowed values" do
      assert {:error, "venue must be one of: home, away, any"} =
               Tools.call("team_record", %{"team" => "Alpha", "venue" => "neutral"}, @data)
    end

    test "When the team is unknown Then the error names it" do
      assert {:error, "Unknown team: Nowhere FC"} =
               Tools.call("team_record", %{"team" => "Nowhere FC"}, @data)
    end

    test "When the tool name is unknown Then an error is returned" do
      assert {:error, "Unknown tool: bogus"} = Tools.call("bogus", %{}, @data)
    end
  end

  describe "Given the provided datasets (end to end)" do
    setup do
      %{data: Store.snapshot()}
    end

    test "When the 2019 standings are requested Then Flamengo is champion on 90 points", %{
      data: data
    } do
      {:ok, text} = Tools.call("standings", %{"season" => 2019}, data)

      assert text =~ "1. Flamengo (RJ) - 90 pts (28W, 6D, 4L) - Champion"
    end

    test "When Flamengo and Fluminense are compared Then both teams appear in the summary", %{
      data: data
    } do
      {:ok, text} =
        Tools.call("head_to_head", %{"team_a" => "Flamengo", "team_b" => "Fluminense"}, data)

      assert text =~ "Flamengo (RJ) vs Fluminense"
      assert text =~ ~r/Matches: \d+/
    end

    test "When a Brazilian player is searched by name Then the dataset rating is returned", %{
      data: data
    } do
      {:ok, text} = Tools.call("search_players", %{"name" => "Neymar"}, data)

      assert text =~ "Neymar Jr - Overall: 92"
    end

    test "When the overview of Corinthians is requested Then match and squad data are both present",
         %{data: data} do
      {:ok, text} = Tools.call("team_overview", %{"team" => "Corinthians"}, data)

      assert text =~ "Corinthians overview (all data):"
      assert text =~ "- Matches:"
    end
  end
end
