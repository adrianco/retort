defmodule BrasilSoccer.FormatterTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.{Formatter, Match, Matches, Teams, Competitions, Fixtures}

  describe "match_line/1" do
    test "renders date, teams, score, competition and round" do
      m =
        Match.new(%{
          competition: "Brasileirão",
          season: 2023,
          round: "22",
          date: ~D[2023-09-03],
          home_team: "Flamengo-RJ",
          away_team: "Fluminense-RJ",
          home_goal: 2,
          away_goal: 0
        })

      assert Formatter.match_line(m) ==
               "2023-09-03: Flamengo 2-0 Fluminense (Brasileirão Round 22)"
    end

    test "uses the stage label when there is no round" do
      m =
        Match.new(%{
          competition: "Libertadores",
          date: ~D[2013-02-12],
          stage: "group stage",
          home_team: "Nacional (URU)",
          away_team: "Barcelona-EQU",
          home_goal: 2,
          away_goal: 2
        })

      assert Formatter.match_line(m) ==
               "2013-02-12: Nacional 2-2 Barcelona (Libertadores, group stage)"
    end
  end

  describe "matches/2" do
    test "includes a header, the lines, and a count" do
      text = Formatter.matches(Fixtures.matches() |> Enum.take(2), "Recent matches")
      assert text =~ "Recent matches"
      assert text =~ "Flamengo"
      assert text =~ "2 match"
    end

    test "reports when nothing was found" do
      assert Formatter.matches([], "Search") =~ "No matches found"
    end
  end

  describe "head_to_head/1" do
    test "summarises the head-to-head record" do
      h2h = Matches.head_to_head(Fixtures.matches(), "Flamengo", "Fluminense")
      text = Formatter.head_to_head(h2h)
      assert text =~ "Flamengo"
      assert text =~ "Fluminense"
      assert text =~ "2 win"
    end
  end

  describe "record/1" do
    test "renders the team record block" do
      rec = Teams.record(Fixtures.matches(), "Flamengo")
      text = Formatter.record(rec)
      assert text =~ "Flamengo"
      assert text =~ "Wins: 2"
      assert text =~ "Win rate: 40.0%"
    end
  end

  describe "standings/3" do
    test "renders a numbered table with points" do
      table = Competitions.standings(Fixtures.mini_season(), "Brasileirão", 2019)
      text = Formatter.standings(table, "Brasileirão", 2019)
      assert text =~ "2019 Brasileirão"
      assert text =~ "1. Flamengo"
      assert text =~ "12 pts"
    end
  end

  describe "players/2" do
    test "renders a numbered player list" do
      players = Fixtures.players() |> Enum.take(2)
      text = Formatter.players(players, "Players")
      assert text =~ "Neymar Jr"
      assert text =~ "Overall:"
    end
  end
end
