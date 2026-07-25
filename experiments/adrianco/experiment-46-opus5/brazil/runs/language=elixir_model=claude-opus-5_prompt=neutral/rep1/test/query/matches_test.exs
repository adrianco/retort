defmodule BrazilianSoccer.Query.MatchesTest do
  @moduledoc """
  Feature: Match queries

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
  """

  use BrazilianSoccer.GraphCase, async: true

  describe "Scenario: find matches between two teams" do
    test "Given the match data is loaded When I search Flamengo vs Fluminense Then I get matches with date, score and competition",
         %{graph: graph} do
      result = ok!(Matches.search(graph, %{team: "Flamengo", opponent: "Fluminense", limit: 100}))

      assert result.total > 30

      for match <- result.matches do
        assert %Date{} = match.date
        assert match.competition in [:serie_a, :serie_b, :copa_do_brasil, :libertadores]
        assert is_integer(match.home_goals)
        assert is_integer(match.away_goals)

        assert "flamengo" in [match.home_id, match.away_id] or
                 "flamengo-rj" in [match.home_id, match.away_id]
      end
    end

    test "Given a team When I search Then results are newest first", %{graph: graph} do
      result = ok!(Matches.search(graph, %{team: "Palmeiras", limit: 50}))
      dates = Enum.map(result.matches, & &1.date)

      assert dates == Enum.sort(dates, {:desc, Date})
    end
  end

  describe "Scenario: filter matches" do
    test "Given a season and a team Then only that season comes back", %{graph: graph} do
      result = ok!(Matches.search(graph, %{team: "Palmeiras", season: 2023, limit: :all}))

      assert result.total > 30
      assert Enum.all?(result.matches, &(&1.season == 2023))
    end

    test "Given a competition Then only that competition comes back", %{graph: graph} do
      result =
        ok!(Matches.search(graph, %{team: "Grêmio", competition: "Libertadores", limit: :all}))

      assert Enum.all?(result.matches, &(&1.competition == :libertadores))
    end

    test "Given a venue Then home and away can be separated", %{graph: graph} do
      {:ok, team} = Graph.find_team(graph, "Corinthians")
      home = ok!(Matches.search(graph, %{team: "Corinthians", venue: "home", limit: :all}))
      away = ok!(Matches.search(graph, %{team: "Corinthians", venue: "away", limit: :all}))

      assert Enum.all?(home.matches, &(&1.home_id == team.id))
      assert Enum.all?(away.matches, &(&1.away_id == team.id))
      assert home.total + away.total == team.match_count
    end

    test "Given a date range Then only matches inside it come back", %{graph: graph} do
      result =
        ok!(
          Matches.search(graph, %{
            team: "Santos",
            date_from: "2019-01-01",
            date_to: "2019-12-31",
            limit: :all
          })
        )

      assert result.total > 0

      assert Enum.all?(result.matches, fn match ->
               Date.compare(match.date, ~D[2019-01-01]) != :lt and
                 Date.compare(match.date, ~D[2019-12-31]) != :gt
             end)
    end

    test "Given a stage Then only that round of the bracket comes back", %{graph: graph} do
      result =
        ok!(Matches.search(graph, %{competition: "Copa do Brasil", stage: "final", limit: :all}))

      assert result.total > 10
      assert Enum.all?(result.matches, &(&1.stage == "final"))
    end

    test "Given the stage \"final\" Then semi-finals are not included", %{graph: graph} do
      result =
        ok!(Matches.search(graph, %{competition: "Libertadores", stage: "final", limit: :all}))

      assert Enum.all?(result.matches, &(&1.stage == "final"))
      refute Enum.any?(result.matches, &(&1.stage == "semifinals"))
    end

    test "Given a round number Then only that round comes back", %{graph: graph} do
      result =
        ok!(
          Matches.search(graph, %{competition: "Brasileirão", season: 2019, round: 38, limit: :all})
        )

      assert result.total == 10
    end

    test "Given no filters at all Then the whole graph is searchable", %{graph: graph} do
      result = ok!(Matches.search(graph, %{limit: 5}))

      assert result.total == map_size(graph.matches)
      assert length(result.matches) == 5
    end
  end

  describe "Scenario: head-to-head" do
    test "Given two teams Then wins, draws and goals are counted from both sides", %{graph: graph} do
      result = ok!(Matches.head_to_head(graph, %{team_a: "Flamengo", team_b: "Fluminense"}))
      s = result.summary

      assert s.matches == s.team_a_wins + s.team_b_wins + s.draws
      assert s.team_a_goals > 0 and s.team_b_goals > 0
      assert Date.compare(result.last_meeting.date, result.first_meeting.date) == :gt
      assert Map.has_key?(result.by_competition, :serie_a)
    end

    test "Given the same pair in the other order Then the record mirrors", %{graph: graph} do
      forward = ok!(Matches.head_to_head(graph, %{team_a: "Palmeiras", team_b: "Santos"}))
      backward = ok!(Matches.head_to_head(graph, %{team_a: "Santos", team_b: "Palmeiras"}))

      assert forward.summary.matches == backward.summary.matches
      assert forward.summary.team_a_wins == backward.summary.team_b_wins
      assert forward.summary.team_a_goals == backward.summary.team_b_goals
    end

    test "Given a competition filter Then only those meetings count", %{graph: graph} do
      result =
        ok!(
          Matches.head_to_head(graph, %{
            team_a: "Grêmio",
            team_b: "Internacional",
            competition: "Brasileirão"
          })
        )

      assert Map.keys(result.by_competition) == [:serie_a]
    end

    test "Given two teams that never met Then the record is empty rather than an error", %{
      graph: graph
    } do
      result = ok!(Matches.head_to_head(graph, %{team_a: "Boca Juniors", team_b: "Avaí"}))

      assert result.summary.matches == 0
      assert result.matches == []
    end

    test "Given a missing team Then an error explains which one", %{graph: graph} do
      assert {:error, {:team_not_found, "Real Madrid", _}} =
               Matches.head_to_head(graph, %{team_a: "Real Madrid", team_b: "Flamengo"})

      assert {:error, {:missing_argument, :team_a}} =
               Matches.head_to_head(graph, %{team_b: "Flamengo"})
    end
  end

  describe "Scenario: last meeting" do
    test "Given two rivals Then the most recent match comes back with its score", %{graph: graph} do
      result = ok!(Matches.last_meeting(graph, "Flamengo", "Corinthians"))

      assert %Match{} = result.match
      assert result.match.date == result.matches |> hd() |> Map.get(:date)
      assert Match.played?(result.match)
      assert result.total > 20
    end
  end

  describe "Scenario: derbies" do
    test "Given a season Then the classic rivalries of that season come back", %{graph: graph} do
      result = ok!(Matches.derbies(graph, %{season: 2023}))

      names = Enum.map(result.derbies, & &1.name)
      assert "Fla-Flu" in names
      assert "Derby Paulista" in names
      assert "Gre-Nal" in names
      assert Enum.all?(result.derbies, &(&1.total > 0))

      assert Enum.all?(result.derbies, fn derby ->
               Enum.all?(derby.matches, &(&1.season == 2023))
             end)
    end

    test "Given a team Then only its rivalries come back", %{graph: graph} do
      result = ok!(Matches.derbies(graph, %{team: "Grêmio"}))

      assert Enum.map(result.derbies, & &1.name) == ["Gre-Nal"]
    end
  end

  describe "Scenario: bad arguments" do
    test "Given an unknown competition Then the error lists the known ones", %{graph: graph} do
      assert {:error, {:unknown_competition, "Premier League", known}} =
               Matches.search(graph, %{competition: "Premier League"})

      assert :serie_a in known
    end

    test "Given an unparseable date Then the error says so", %{graph: graph} do
      assert {:error, {:invalid_date, "yesterday"}} =
               Matches.search(graph, %{date_from: "yesterday"})
    end

    test "Given an unknown venue Then the error says so", %{graph: graph} do
      assert {:error, {:invalid_venue, "stadium"}} =
               Matches.search(graph, %{team: "Santos", venue: "stadium"})
    end

    test "Given string arguments from JSON Then they are coerced", %{graph: graph} do
      result =
        ok!(
          Matches.search(graph, %{
            "team" => "Palmeiras",
            "season" => "2019",
            "competition" => "serie a",
            "limit" => "3"
          })
        )

      assert length(result.matches) == 3
      assert Enum.all?(result.matches, &(&1.season == 2019 and &1.competition == :serie_a))
    end
  end
end
