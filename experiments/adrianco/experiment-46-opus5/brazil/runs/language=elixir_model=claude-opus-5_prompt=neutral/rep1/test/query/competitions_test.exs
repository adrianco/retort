defmodule BrazilianSoccer.Query.CompetitionsTest do
  @moduledoc """
  Feature: Competition queries

  Scenario: League tables computed from results
    Given the match data is loaded
    When I ask for the 2019 Brasileirão standings
    Then Flamengo tops the table on 90 points
    And the bottom four are marked as relegated
  """

  use BrazilianSoccer.GraphCase, async: true

  describe "Scenario: listing competitions" do
    test "Given the graph Then every competition reports seasons and counts", %{graph: graph} do
      result = ok!(Competitions.list(graph))
      ids = Enum.map(result.competitions, & &1.competition.id)

      assert ids == [:serie_a, :serie_b, :serie_c, :copa_do_brasil, :libertadores]

      serie_a = Enum.find(result.competitions, &(&1.competition.id == :serie_a))
      assert serie_a.season_range == {2003, 2023}
      assert serie_a.matches > 8_000
      assert serie_a.teams > 40
    end
  end

  describe "Scenario: league standings" do
    test "Given 2019 Then the table matches the real Brasileirão", %{graph: graph} do
      result = ok!(Competitions.standings(graph, %{competition: "Brasileirão", season: 2019}))

      assert length(result.table) == 20
      assert result.matches_counted == 380

      [champion, runner_up | _] = result.table
      assert champion.team.name == "Flamengo"
      assert champion.record.points == 90
      assert champion.record.wins == 28
      assert champion.record.draws == 6
      assert champion.record.losses == 4
      assert champion.record.goals_for == 86
      assert runner_up.team.name == "Santos"

      assert result.champion.name == "Flamengo"
      assert Enum.map(result.relegated, & &1.name) == ["Cruzeiro", "CSA", "Chapecoense", "Avaí"]
    end

    test "Given a table Then positions are ordered by points, wins then goal difference", %{
      graph: graph
    } do
      result = ok!(Competitions.standings(graph, %{season: 2018}))

      keys =
        Enum.map(result.table, fn row ->
          {-row.record.points, -row.record.wins, -row.record.goal_difference}
        end)

      assert keys == Enum.sort(keys)
      assert Enum.map(result.table, & &1.position) == Enum.to_list(1..length(result.table))
    end

    test "Given a home-only table Then only home matches count and nobody is relegated", %{
      graph: graph
    } do
      result = ok!(Competitions.standings(graph, %{season: 2019, venue: "home"}))

      assert Enum.all?(result.table, &(&1.record.matches == 19))
      assert result.relegated == []
      assert result.champion == nil
    end

    test "Given a season the data covers only partly Then the answer warns about it", %{
      graph: graph
    } do
      result = ok!(Competitions.standings(graph, %{season: 2023}))

      assert result.matches_counted < result.expected_matches
      assert result.note =~ "Careful"
    end

    test "Given a season with no data Then the error lists what is available", %{graph: graph} do
      assert {:error, {:no_data, :serie_a, 1975, seasons}} =
               Competitions.standings(graph, %{season: 1975})

      assert 2019 in seasons
    end

    test "Given no season Then the error says it is required", %{graph: graph} do
      assert {:error, {:missing_argument, :season}} = Competitions.standings(graph, %{})
    end
  end

  describe "Scenario: champions" do
    test "Given a league season Then the champion is the top of the computed table", %{
      graph: graph
    } do
      for {season, champion} <- [
            {2019, "Flamengo"},
            {2018, "Palmeiras"},
            {2017, "Corinthians"},
            {2016, "Palmeiras"},
            {2014, "Cruzeiro"}
          ] do
        result = ok!(Competitions.champion(graph, %{competition: "Brasileirão", season: season}))
        assert result.champion.name == champion, "wrong champion for #{season}"
        assert result.basis == :league_table
      end
    end

    test "Given a cup season Then the champion is the winner of the final on aggregate", %{
      graph: graph
    } do
      result =
        ok!(Competitions.champion(graph, %{competition: "Copa do Brasil", season: 2019}))

      assert result.champion.name == "Athletico Paranaense"
      assert result.runner_up.name == "Internacional"
      assert result.basis == :final
      assert length(result.detail.legs) == 2
      assert result.note =~ "penalty"
    end

    test "Given the Libertadores Then the champion comes from the final", %{graph: graph} do
      for {season, champion} <- [{2019, "Flamengo"}, {2018, "River Plate"}, {2017, "Grêmio"}] do
        result = ok!(Competitions.champion(graph, %{competition: "Libertadores", season: season}))
        assert result.champion.name == champion, "wrong champion for #{season}"
      end
    end

    test "Given a final decided on penalties Then the answer refuses to guess a winner", %{
      graph: graph
    } do
      # 2013: Atlético Mineiro and Olimpia drew 2-2 on aggregate and the cup was
      # settled by a shoot-out, which the datasets do not record.
      result = ok!(Competitions.champion(graph, %{competition: "Libertadores", season: 2013}))

      assert result.champion == nil
      assert result.detail.undecided
      assert length(result.detail.finalists) == 2
    end

    test "Given a season missing a match Then the table warns instead of pretending", %{
      graph: graph
    } do
      # the 2009 files are one Flamengo match short, so the computed table
      # disagrees with the official one — the note has to say so
      result = ok!(Competitions.standings(graph, %{season: 2009}))

      assert result.matches_counted == 379
      assert result.note =~ "379 of the 380 matches"
    end
  end

  describe "Scenario: cup brackets" do
    test "Given a Libertadores season Then the stages come back in order", %{graph: graph} do
      result = ok!(Competitions.bracket(graph, %{competition: "Libertadores", season: 2018}))

      stages = Enum.map(result.stages, & &1.stage)
      assert stages == ["group stage", "round of 16", "quarterfinals", "semifinals", "final"]
      assert result.champion.champion.name == "River Plate"
    end

    test "Given a Copa do Brasil season Then derived stages appear", %{graph: graph} do
      result = ok!(Competitions.bracket(graph, %{competition: "Copa do Brasil", season: 2019}))
      stages = Enum.map(result.stages, & &1.stage)

      assert "final" in stages
      assert "semifinals" in stages
    end
  end

  describe "Scenario: competition summary" do
    test "Given a season Then goals, home advantage and top teams come back", %{graph: graph} do
      result = ok!(Competitions.summary(graph, %{competition: "Brasileirão", season: 2019}))

      assert result.matches == 380
      assert result.teams == 20
      assert_in_delta result.goals_per_match, 2.3, 0.3
      assert_in_delta result.home_win_rate + result.draw_rate + result.away_win_rate, 100.0, 0.2
      assert length(result.top_scoring_teams) == 5
      assert hd(result.top_scoring_teams).team.name == "Flamengo"
      assert result.champion.champion.name == "Flamengo"
    end

    test "Given no season Then the whole competition is summarised", %{graph: graph} do
      result = ok!(Competitions.summary(graph, %{competition: "Libertadores"}))

      assert result.season == nil
      assert result.matches > 1_000
      assert result.champion == nil
    end
  end
end
