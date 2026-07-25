defmodule BrazilianSoccer.Query.TeamsTest do
  @moduledoc """
  Feature: Team queries

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
  """

  use BrazilianSoccer.GraphCase, async: true

  describe "Scenario: team statistics for a season" do
    test "Given the data When I ask for Palmeiras in 2023 Then wins, draws, losses and goals come back",
         %{graph: graph} do
      result = ok!(Teams.stats(graph, %{team: "Palmeiras", season: 2023}))
      record = result.record

      assert result.team.name == "Palmeiras"
      assert record.matches == record.wins + record.draws + record.losses
      assert record.goals_for > 0
      assert record.goals_against > 0
      assert record.points == record.wins * 3 + record.draws
      assert record.goal_difference == record.goals_for - record.goals_against
      assert record.win_rate == Float.round(record.wins * 100 / record.matches, 1)
    end

    test "Given a home-only filter Then only home matches are counted", %{graph: graph} do
      result =
        ok!(
          Teams.stats(graph, %{
            team: "Corinthians",
            season: 2022,
            competition: "Brasileirão",
            venue: "home"
          })
        )

      assert result.record.matches == 19
      assert result.record == result.home
      assert result.away.matches == 0
    end

    test "Given no filters Then home and away split adds up to the whole record", %{graph: graph} do
      result = ok!(Teams.stats(graph, %{team: "Santos"}))

      assert result.home.matches + result.away.matches == result.record.matches
      assert result.home.wins + result.away.wins == result.record.wins
      assert result.home.goals_for + result.away.goals_for == result.record.goals_for
    end

    test "Given a team Then form, best win and worst defeat come back", %{graph: graph} do
      result = ok!(Teams.stats(graph, %{team: "Flamengo"}))

      assert length(result.form) == 5
      assert Enum.all?(result.form, &(&1.symbol in ["W", "D", "L", "?"]))
      assert Match.outcome_for(result.biggest_win, result.team.id) == :win
      assert Match.outcome_for(result.biggest_loss, result.team.id) == :loss
    end

    test "Given a competition breakdown Then every competition the team played shows up", %{
      graph: graph
    } do
      result = ok!(Teams.stats(graph, %{team: "Grêmio"}))
      competitions = Enum.map(result.by_competition, fn {competition, _} -> competition end)

      assert :serie_a in competitions
      assert :libertadores in competitions
      assert :copa_do_brasil in competitions
    end

    test "Given a season with no matches Then the record is empty, not an error", %{graph: graph} do
      result = ok!(Teams.stats(graph, %{team: "Palmeiras", season: 1999}))

      assert result.record.matches == 0
    end

    test "Given a missing team argument Then the error says which one", %{graph: graph} do
      assert {:error, {:missing_argument, :team}} = Teams.stats(graph, %{season: 2019})
    end
  end

  describe "Scenario: team profile" do
    test "Given a club Then identity, spellings, seasons and record come back", %{graph: graph} do
      result = ok!(Teams.profile(graph, %{team: "Sport Recife"}))

      assert result.team.name == "Sport Recife"
      assert result.team.state == "PE"
      assert "Sport-PE" in result.team.aliases
      assert result.record.matches > 200
      assert result.first_match.date.year <= 2012
      assert result.player_count > 0
    end

    test "Given a club with no FIFA players Then the profile still works", %{graph: graph} do
      result = ok!(Teams.profile(graph, %{team: "Corinthians"}))

      assert result.player_count == 0
      assert result.record.matches > 500
    end
  end

  describe "Scenario: comparing two teams" do
    test "Given two clubs Then both records and the head-to-head come back", %{graph: graph} do
      result = ok!(Teams.compare(graph, %{team_a: "Palmeiras", team_b: "Santos"}))

      assert result.team_a.team.name == "Palmeiras"
      assert result.team_b.team.name == "Santos"
      assert result.head_to_head.summary.matches > 30

      assert result.head_to_head.summary.matches ==
               result.head_to_head.summary.team_a_wins +
                 result.head_to_head.summary.team_b_wins +
                 result.head_to_head.summary.draws
    end

    test "Given a season Then the comparison is limited to it", %{graph: graph} do
      result = ok!(Teams.compare(graph, %{team_a: "Grêmio", team_b: "Internacional", season: 2019}))

      assert result.team_a.record.matches < 60
      assert Enum.all?(result.head_to_head.matches, &(&1.season == 2019))
    end
  end

  describe "Scenario: rankings" do
    test "Given the home metric Then teams are ranked by home win rate", %{graph: graph} do
      result =
        ok!(Teams.rankings(graph, %{metric: "home", competition: "Brasileirão", limit: 5}))

      rates = Enum.map(result.rankings, & &1.record.win_rate)
      assert rates == Enum.sort(rates, :desc)
      assert length(result.rankings) == 5
      assert result.metric == :home
    end

    test "Given a season and a sort key Then the ranking respects both", %{graph: graph} do
      result =
        ok!(
          Teams.rankings(graph, %{
            metric: "overall",
            competition: "Brasileirão",
            season: 2019,
            sort_by: "points",
            limit: 3
          })
        )

      assert hd(result.rankings).team.name == "Flamengo"
      assert hd(result.rankings).record.points == 90
    end

    test "Given goals_against Then fewest conceded ranks first", %{graph: graph} do
      result =
        ok!(
          Teams.rankings(graph, %{
            competition: "Brasileirão",
            season: 2019,
            sort_by: "goals_against",
            limit: 3
          })
        )

      conceded = Enum.map(result.rankings, & &1.record.goals_against)
      assert conceded == Enum.sort(conceded)
    end

    test "Given a minimum match count Then small samples are excluded", %{graph: graph} do
      result = ok!(Teams.rankings(graph, %{competition: "Copa do Brasil", min_matches: 30}))

      assert Enum.all?(result.rankings, &(&1.record.matches >= 30))
    end
  end
end
