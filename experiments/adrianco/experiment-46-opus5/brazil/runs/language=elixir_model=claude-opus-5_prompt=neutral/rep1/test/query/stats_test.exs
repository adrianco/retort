defmodule BrazilianSoccer.Query.StatsTest do
  @moduledoc """
  Feature: Statistical analysis

  Scenario: Aggregate statistics
    Given the match data is loaded
    When I ask for goals per match, home advantage or biggest wins
    Then the numbers are computed over every matching match, not a page of them
  """

  use BrazilianSoccer.GraphCase, async: true

  describe "Scenario: overview statistics" do
    test "Given a competition Then goals and result rates are consistent", %{graph: graph} do
      result = ok!(Stats.overview(graph, %{competition: "Brasileirão"}))

      assert result.matches > 8_000
      assert result.matches == result.home_wins + result.away_wins + result.draws
      assert_in_delta result.home_win_rate + result.away_win_rate + result.draw_rate, 100.0, 0.2
      assert_in_delta result.goals_per_match, 2.5, 0.5
      assert result.goals == result.home_goals + result.away_goals
    end

    test "Given the whole graph Then every competition shows up in the breakdown", %{graph: graph} do
      result = ok!(Stats.overview(graph, %{}))
      competitions = Enum.map(result.by_competition, fn {competition, _} -> competition end)

      assert :serie_a in competitions
      assert :libertadores in competitions
      assert result.matches > 15_000
    end

    test "Given a season range Then only those seasons are aggregated", %{graph: graph} do
      result =
        ok!(
          Stats.overview(graph, %{competition: "Brasileirão", season_from: 2018, season_to: 2019})
        )

      seasons = Enum.map(result.by_season, fn {season, _} -> season end)
      assert seasons == [2018, 2019]
      assert result.matches == 760
    end

    test "Given a team Then only its matches count", %{graph: graph} do
      {:ok, team} = Graph.find_team(graph, "Flamengo")
      result = ok!(Stats.overview(graph, %{team: "Flamengo"}))

      assert result.matches <= team.match_count
    end

    test "Given filters that match nothing Then an error explains", %{graph: graph} do
      assert {:error, {:no_matches, _}} =
               Stats.overview(graph, %{competition: "Libertadores", season: 1999})
    end
  end

  describe "Scenario: biggest wins" do
    test "Given no filters Then the biggest margins in the whole graph come back", %{graph: graph} do
      result = ok!(Stats.biggest_wins(graph, %{limit: 10}))

      margins = Enum.map(result.matches, &Match.margin/1)
      assert margins == Enum.sort(margins, :desc)
      assert hd(margins) >= 8
      assert length(result.matches) == 10
    end

    test "Given a team Then only wins by that team come back", %{graph: graph} do
      result = ok!(Stats.biggest_wins(graph, %{team: "Palmeiras", limit: 5}))

      assert Enum.all?(result.matches, &(Match.outcome_for(&1, result.team.id) == :win))
    end

    test "Given a competition and season Then the search is scoped", %{graph: graph} do
      result =
        ok!(Stats.biggest_wins(graph, %{competition: "Brasileirão", season: 2019, limit: 3}))

      assert Enum.all?(result.matches, &(&1.competition == :serie_a and &1.season == 2019))
    end
  end

  describe "Scenario: highest scoring matches" do
    test "Given a competition Then matches are ranked by total goals", %{graph: graph} do
      result = ok!(Stats.highest_scoring(graph, %{competition: "Brasileirão", limit: 5}))
      totals = Enum.map(result.matches, &Match.total_goals/1)

      assert totals == Enum.sort(totals, :desc)
      assert hd(totals) >= 8
    end
  end

  describe "Scenario: comparing seasons" do
    test "Given two seasons Then each gets its own block with a champion", %{graph: graph} do
      result =
        ok!(Stats.compare_seasons(graph, %{competition: "Brasileirão", seasons: [2018, 2019]}))

      assert Enum.map(result.seasons, & &1.season) == [2018, 2019]
      assert Enum.all?(result.seasons, & &1.available)
      assert Enum.map(result.seasons, & &1.champion.name) == ["Palmeiras", "Flamengo"]
      assert Enum.all?(result.seasons, &(&1.stats.matches == 380))
      assert Enum.all?(result.seasons, &(&1.top_scoring_team.goals > 50))
    end

    test "Given a season with no data Then it is reported as unavailable", %{graph: graph} do
      result = ok!(Stats.compare_seasons(graph, %{seasons: [2019, 1990]}))

      assert Enum.find(result.seasons, &(&1.season == 1990)).available == false
    end

    test "Given no seasons Then the error says they are required", %{graph: graph} do
      assert {:error, {:missing_argument, :seasons}} = Stats.compare_seasons(graph, %{})
    end
  end

  describe "Scenario: home advantage" do
    test "Given a competition Then home advantage is reported per season", %{graph: graph} do
      result = ok!(Stats.home_advantage(graph, %{competition: "Brasileirão"}))

      assert result.overall.home_win_rate > result.overall.away_win_rate
      assert length(result.by_season) == 21

      assert Enum.all?(result.by_season, fn {_season, stats} ->
               stats.home_win_rate >= 0 and stats.home_win_rate <= 100
             end)
    end

    test "Given the Libertadores Then home advantage is also computable", %{graph: graph} do
      result = ok!(Stats.home_advantage(graph, %{competition: "Libertadores"}))

      assert result.overall.matches > 1_000
      assert result.overall.home_goals > result.overall.away_goals
    end
  end
end
