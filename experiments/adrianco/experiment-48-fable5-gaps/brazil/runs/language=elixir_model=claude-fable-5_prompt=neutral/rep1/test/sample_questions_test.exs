defmodule BrazilianSoccerMcp.SampleQuestionsTest do
  @moduledoc """
  BDD acceptance tests: the specification's success criteria require at least
  20 sample questions to be answerable through the MCP tools. Each test states
  the natural-language question and drives the same tool call an LLM client
  would make.
  """

  use ExUnit.Case, async: true

  alias BrazilianSoccerMcp.Tools

  defp ask(tool, args) do
    assert {:ok, text} = Tools.call(tool, args)
    text
  end

  describe "Given the loaded datasets, match queries" do
    test ~s(Q1 "Show me all Flamengo vs Fluminense matches") do
      text = ask("head_to_head", %{"team1" => "Flamengo", "team2" => "Fluminense"})
      assert text =~ "Flamengo vs Fluminense"
      assert text =~ ~r/\d{4}-\d{2}-\d{2}/
      assert text =~ "Head-to-head in dataset"
    end

    test ~s(Q2 "What matches did Palmeiras play in 2023?") do
      text = ask("search_matches", %{"team" => "Palmeiras", "season" => 2023})
      assert text =~ "Palmeiras"
      assert text =~ "2023-"
    end

    test ~s(Q3 "Find all Copa Libertadores finals") do
      text = ask("search_matches", %{"competition" => "Libertadores", "stage" => "final"})
      assert text =~ "Copa Libertadores final"
      refute text =~ "semifinals"
    end

    test ~s(Q4 "When did Flamengo last play Corinthians, and what was the score?") do
      text =
        ask("search_matches", %{"team" => "Flamengo", "opponent" => "Corinthians", "limit" => 1})

      # most recent match first, with a score line
      assert text =~ ~r/- \d{4}-\d{2}-\d{2}: .*(\d+-\d+)/
    end

    test ~s(Q5 "Show me Santos matches from the 2019 season only") do
      text = ask("search_matches", %{"team" => "Santos", "season" => 2019})
      assert text =~ "Santos"
      assert text =~ "2019-"
      refute text =~ "2018-"
    end

    test ~s(Q6 "What Copa do Brasil matches were played in 2019?") do
      text = ask("search_matches", %{"competition" => "Copa do Brasil", "season" => 2019})
      assert text =~ "Copa do Brasil"
    end

    test ~s(Q7 "Which matches happened between June and July 2014?") do
      text =
        ask("search_matches", %{
          "competition" => "Brasileirão",
          "date_from" => "2014-06-01",
          "date_to" => "2014-07-31"
        })

      assert text =~ "2014-0"
      refute text =~ "2014-05"
    end
  end

  describe "Given the loaded datasets, team queries" do
    test ~s(Q8 "What is Corinthians' home record in 2022?") do
      text =
        ask("team_stats", %{
          "team" => "Corinthians",
          "season" => 2022,
          "competition" => "Brasileirão",
          "venue" => "home"
        })

      assert text =~ "Matches: 19"
      assert text =~ ~r/Wins: \d+, Draws: \d+, Losses: \d+/
      assert text =~ ~r/Win rate: [\d.]+%/
    end

    test ~s(Q9 "Compare Palmeiras and Santos head-to-head") do
      text = ask("head_to_head", %{"team1" => "Palmeiras", "team2" => "Santos"})
      assert text =~ "Palmeiras"
      assert text =~ "Santos"
      assert text =~ ~r/\d+ wins.*\d+ wins.*\d+ draws/
    end

    test ~s(Q10 "How has Grêmio performed across all competitions?") do
      text = ask("team_stats", %{"team" => "Grêmio"})
      assert text =~ "By competition:"
      assert text =~ "Brasileirão Série A"
      assert text =~ "Copa Libertadores"
    end

    test ~s(Q11 "What competitions has Palmeiras played in?") do
      text = ask("team_stats", %{"team" => "Palmeiras"})
      assert text =~ "Brasileirão Série A"
      assert text =~ "Copa do Brasil"
      assert text =~ "Copa Libertadores"
    end

    test ~s(Q12 "Which team has the best home record?" - via home venue stats) do
      # An LLM would compare candidates; verify home stats work for several teams
      for team <- ["Flamengo", "Palmeiras", "São Paulo"] do
        text = ask("team_stats", %{"team" => team, "venue" => "home"})
        assert text =~ "home matches only"
        assert text =~ ~r/Win rate: [\d.]+%/
      end
    end
  end

  describe "Given the loaded datasets, player queries" do
    test ~s(Q13 "Who is Neymar?") do
      text = ask("search_players", %{"name" => "Neymar"})
      assert text =~ "Neymar Jr"
      assert text =~ "Overall: 92"
      assert text =~ "Position: LW"
      assert text =~ "Paris Saint-Germain"
    end

    test ~s(Q14 "Find the top Brazilian players in the dataset") do
      text = ask("top_players", %{"nationality" => "Brazil", "limit" => 5})
      assert text =~ "Neymar Jr"
      assert text =~ "Overall: 92"
    end

    test ~s(Q15 "Which players play for Santos?") do
      text =
        ask("search_players", %{"club" => "Santos", "nationality" => "Brazil", "limit" => 30})

      assert text =~ "Santos"
      assert text =~ ~r/1\. .+ - Overall: \d+/
    end

    test ~s(Q16 "Show me Brazilian goalkeepers rated 85 or better") do
      text =
        ask("search_players", %{
          "nationality" => "Brazil",
          "position" => "goalkeeper",
          "min_overall" => 85
        })

      assert text =~ "Alisson"
      assert text =~ "Ederson"
    end

    test ~s(Q17 "Who are the best forwards at Grêmio?") do
      text = ask("top_players", %{"club" => "Grêmio", "position" => "forward"})
      assert text =~ ~r/Overall: \d+/
    end

    test ~s(Q18 "Which players play for Flamengo?" - absent club handled gracefully) do
      # FIFA 19 licensing omits Flamengo; the answer must explain, not error
      text = ask("search_players", %{"club" => "Flamengo"})
      assert text =~ "no players found"
      assert text =~ "FIFA"
    end
  end

  describe "Given the loaded datasets, competition queries" do
    test ~s(Q19 "Who won the 2019 Brasileirão?") do
      text = ask("league_standings", %{"season" => 2019})
      assert text =~ ~r/1\. Flamengo - 90 pts \(28W, 6D, 4L.*\) - Champion/
    end

    test ~s(Q20 "Show the top of the 2003 Brasileirão table" - historical file) do
      text = ask("league_standings", %{"season" => 2003, "limit" => 5})
      assert text =~ ~r/1\. Cruzeiro - \d+ pts.*Champion/
    end

    test ~s(Q21 "Which teams were at the bottom in 2013?" - relegation zone) do
      text = ask("league_standings", %{"season" => 2013, "limit" => 20})
      lines = String.split(text, "\n")
      assert length(lines) == 21
      assert List.last(lines) =~ "20."
    end

    test ~s(Q22 "Compare the 2018 and 2019 seasons") do
      t2018 = ask("competition_stats", %{"competition" => "Brasileirão", "season" => 2018})
      t2019 = ask("competition_stats", %{"competition" => "Brasileirão", "season" => 2019})
      assert t2018 =~ "Matches: 380"
      assert t2019 =~ "Matches: 380"
      assert t2018 =~ "Average goals per match"
      assert t2019 =~ "Average goals per match"
    end
  end

  describe "Given the loaded datasets, statistical analysis" do
    test ~s(Q23 "What's the average goals per match in the Brasileirão?") do
      text = ask("competition_stats", %{"competition" => "Brasileirão"})
      assert text =~ ~r/Average goals per match: [12]\.\d+/
      assert text =~ ~r/Home wins: \d+ \([\d.]+%\)/
    end

    test ~s(Q24 "Show me the biggest wins in the dataset") do
      text = ask("biggest_wins", %{"limit" => 5})
      assert text =~ ~r/1\. \d{4}-\d{2}-\d{2}: .+ \d+-\d+ .+/
      # top margin in these datasets is at least 6 goals
      [_, hg, ag] = Regex.run(~r/1\. \d{4}-\d{2}-\d{2}: .+? (\d+)-(\d+) /, text)
      assert abs(String.to_integer(hg) - String.to_integer(ag)) >= 6
    end

    test ~s(Q25 "What were Flamengo's biggest wins in 2019?") do
      text = ask("biggest_wins", %{"team" => "Flamengo", "season" => 2019, "limit" => 3})
      assert text =~ "Flamengo"
      assert text =~ "2019-"
    end

    test ~s(Q26 "What teams are in the dataset?" - discovery) do
      text = ask("list_teams", %{"search" => "botafogo"})
      assert text =~ "Botafogo"
      assert text =~ "Botafogo-PB"
    end
  end

  describe "Given the success criteria, performance" do
    @tag :performance
    test "simple lookups respond in under 2 seconds" do
      {micros, {:ok, _}} =
        :timer.tc(fn ->
          Tools.call("search_matches", %{"team" => "Flamengo", "opponent" => "Corinthians"})
        end)

      assert micros < 2_000_000
    end

    @tag :performance
    test "aggregate queries respond in under 5 seconds" do
      {micros, {:ok, _}} =
        :timer.tc(fn -> Tools.call("competition_stats", %{"competition" => "Brasileirão"}) end)

      assert micros < 5_000_000

      {micros2, {:ok, _}} =
        :timer.tc(fn -> Tools.call("league_standings", %{"season" => 2019}) end)

      assert micros2 < 5_000_000
    end
  end
end
