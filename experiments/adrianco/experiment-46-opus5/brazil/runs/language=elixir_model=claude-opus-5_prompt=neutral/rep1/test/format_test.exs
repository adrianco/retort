defmodule BrazilianSoccer.FormatTest do
  @moduledoc """
  Feature: Readable answers

  The MCP text content is what the model quotes back to the user, so it has to
  read like the examples in the specification.
  """

  use BrazilianSoccer.GraphCase, async: true

  alias BrazilianSoccer.Format

  describe "Scenario: match lines" do
    test "Given a played match Then the line has date, teams, score and context", %{graph: graph} do
      result = ok!(Matches.search(graph, %{team: "Flamengo", season: 2019, limit: 1}))
      line = Format.match_line(hd(result.matches))

      assert line =~ ~r/^\d{4}-\d{2}-\d{2}: .+ \d+-\d+ .+ \(.+\)$/
      assert line =~ "Flamengo"
    end

    test "Given a match with no score Then the line says the result is missing", %{graph: graph} do
      result =
        ok!(Matches.search(graph, %{competition: "Libertadores", stage: "final", limit: :all}))

      unplayed = Enum.find(result.matches, &(not Match.played?(&1)))
      assert Format.match_line(unplayed) =~ "[result not in dataset]"
    end

    test "Given canonical ids Then the display name is used, not the raw spelling", %{graph: g} do
      result = ok!(Matches.search(g, %{team: "Athletico Paranaense", season: 2019, limit: 1}))
      line = Format.match_line(hd(result.matches))

      assert line =~ "Athletico Paranaense"
      refute line =~ "Atletico-PR"
    end
  end

  describe "Scenario: answers follow the shapes in the specification" do
    test "Given a head-to-head Then it reads like the example", %{graph: graph} do
      text =
        graph
        |> Matches.head_to_head(%{team_a: "Flamengo", team_b: "Fluminense"})
        |> ok!()
        |> Format.head_to_head()

      assert text =~ "Flamengo vs Fluminense"
      assert text =~ ~r/Head-to-head in dataset: Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws/
      assert text =~ "Most recent meetings:"
    end

    test "Given team statistics Then matches, wins, goals and win rate are listed", %{graph: graph} do
      text =
        graph
        |> Teams.stats(%{
          team: "Corinthians",
          season: 2022,
          competition: "Brasileirão",
          venue: "home"
        })
        |> ok!()
        |> Format.team_stats()

      assert text =~ "Corinthians"
      assert text =~ "- Matches: 19"
      assert text =~ ~r/- Wins: \d+, Draws: \d+, Losses: \d+/
      assert text =~ ~r/- Goals For: \d+, Goals Against: \d+/
      assert text =~ "Win rate:"
    end

    test "Given standings Then positions, points and the champion are marked", %{graph: graph} do
      text =
        graph
        |> Competitions.standings(%{season: 2019})
        |> ok!()
        |> Format.standings()

      assert text =~ "1. Flamengo - 90 pts (28W, 6D, 4L, 86-37, +49) - Champion"
      assert text =~ "20. Avaí"
      assert text =~ "Relegated"
      assert text =~ "Table computed from the match results"
    end

    test "Given a player list Then each line shows rating, position and club", %{graph: graph} do
      text =
        graph
        |> Players.search(%{nationality: "Brazil", sort_by: "overall", limit: 3})
        |> ok!()
        |> Format.players()

      assert text =~ "1. Neymar Jr - Overall: 92 - Position: LW - Club: Paris Saint-Germain"
      assert text =~ "(824 more)"
    end

    test "Given a squad Then the club summary and top players are listed", %{graph: graph} do
      text = graph |> Players.club_squad(%{club: "Grêmio"}) |> ok!() |> Format.club_squad()

      assert text =~ "Grêmio squad in the FIFA dataset: 20 players"
      assert text =~ "Average rating:"
      assert text =~ "Recent matches:"
    end

    test "Given statistics Then goals per match and home win rate are reported", %{graph: graph} do
      text =
        graph |> Stats.overview(%{competition: "Brasileirão"}) |> ok!() |> Format.stats_overview()

      assert text =~ ~r/average \d\.\d+ per match/
      assert text =~ ~r/Home wins: \d+\.\d+%/
    end

    test "Given biggest wins Then they are numbered by margin", %{graph: graph} do
      text = graph |> Stats.biggest_wins(%{limit: 3}) |> ok!() |> Format.biggest_wins()

      assert text =~ "Biggest victories"
      assert text =~ "1. "
      assert text =~ "3. "
    end
  end

  describe "Scenario: error messages" do
    test "Given an unknown team Then the message suggests alternatives" do
      message = Format.error({:team_not_found, "Barcelona FC", ["Bahia", "Botafogo"]})

      assert message =~ "No team called \"Barcelona FC\""
      assert message =~ "Bahia"
    end

    test "Given a club missing from the FIFA export Then the message explains why" do
      message = Format.error({:club_not_in_player_data, "Flamengo", ["Grêmio", "Santos"]})

      assert message =~ "does not license every Brazilian club"
      assert message =~ "Grêmio"
    end

    test "Given other failures Then each has a human readable message" do
      assert Format.error({:missing_argument, :season}) =~ "Missing required argument: season"
      assert Format.error({:unknown_competition, "MLS", [:serie_a]}) =~ "Unknown competition"
      assert Format.error({:invalid_date, "soon"}) =~ "YYYY-MM-DD"
      assert Format.error({:no_data, :serie_a, 1975, [2019]}) =~ "Available seasons"
      assert Format.error({:some, :unknown, :shape}) =~ "Query failed"
    end
  end

  describe "Scenario: no results" do
    test "Given a search with no hits Then the answer says so plainly", %{graph: graph} do
      text =
        graph
        |> Matches.search(%{team: "Palmeiras", season: 1999})
        |> ok!()
        |> Format.matches()

      assert text =~ "No matches in the dataset"
    end
  end
end
