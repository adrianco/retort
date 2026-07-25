defmodule BrazilianSoccer.Query.PlayersTest do
  @moduledoc """
  Feature: Player queries

  Scenario: Find players
    Given the FIFA player data is loaded
    When I filter by name, nationality, club or position
    Then I should receive matching players with ratings and attributes
  """

  use BrazilianSoccer.GraphCase, async: true

  describe "Scenario: search by name" do
    test "Given a partial name Then matching players come back", %{graph: graph} do
      result = ok!(Players.search(graph, %{name: "Neymar"}))

      assert result.total >= 1
      assert hd(result.players).name =~ "Neymar"
      assert hd(result.players).overall == 92
    end

    test "Given an accented query Then accents do not matter", %{graph: graph} do
      with_accent = ok!(Players.search(graph, %{name: "Rodríguez"}))
      without_accent = ok!(Players.search(graph, %{name: "Rodriguez"}))

      assert with_accent.total == without_accent.total
      assert with_accent.total > 10
    end
  end

  describe "Scenario: filter by nationality, club and position" do
    test "Given Brazil Then only Brazilian players come back", %{graph: graph} do
      result = ok!(Players.search(graph, %{nationality: "Brazil", limit: :all}))

      assert result.total == 827
      assert Enum.all?(result.players, &(&1.nationality == "Brazil"))
    end

    test "Given a Brazilian club Then only that club's players come back", %{graph: graph} do
      result = ok!(Players.search(graph, %{club: "Grêmio", limit: :all}))

      assert result.total == 20
      assert Enum.all?(result.players, &(&1.club == "Grêmio"))
    end

    test "Given a club name that also matches a foreign club Then only the linked club is used",
         %{graph: graph} do
      result = ok!(Players.search(graph, %{club: "Santos", limit: :all}))

      # not Santos Laguna of Mexico
      assert Enum.all?(result.players, &(&1.club == "Santos"))
      refute Enum.any?(result.players, &(&1.club =~ "Laguna"))
    end

    test "Given a club only the player data knows Then it is still searchable", %{graph: graph} do
      # "Santos Laguna" fuzzily resolves to Santos of São Paulo when looking up
      # teams, but a player search must not silently answer about the wrong club
      result = ok!(Players.search(graph, %{club: "Santos Laguna", limit: :all}))

      assert result.total > 0
      assert Enum.all?(result.players, &(&1.club == "Santos Laguna"))
    end

    test "Given a position group Then only those positions come back", %{graph: graph} do
      result = ok!(Players.search(graph, %{position_group: "goalkeeper", limit: 50}))

      assert Enum.all?(result.players, &(&1.position == "GK"))
    end

    test "Given a FIFA position code Then it filters exactly", %{graph: graph} do
      result = ok!(Players.search(graph, %{position: "CAM", limit: 10}))

      assert Enum.all?(result.players, &(&1.position == "CAM"))
    end

    test "Given rating and age bounds Then they are respected", %{graph: graph} do
      result =
        ok!(
          Players.search(graph, %{
            nationality: "Brazil",
            min_overall: 85,
            max_age: 30,
            limit: :all
          })
        )

      assert result.total > 0
      assert Enum.all?(result.players, &(&1.overall >= 85 and &1.age <= 30))
    end

    test "Given brazilian_clubs_only Then every player links to a club node", %{graph: graph} do
      result =
        ok!(Players.search(graph, %{brazilian_clubs_only: true, limit: :all}))

      assert result.total > 100
      assert Enum.all?(result.players, &(&1.club_id != nil))
    end
  end

  describe "Scenario: sorting" do
    test "Given sort_by overall Then the best rated come first", %{graph: graph} do
      result = ok!(Players.search(graph, %{nationality: "Brazil", sort_by: "overall", limit: 10}))
      ratings = Enum.map(result.players, & &1.overall)

      assert ratings == Enum.sort(ratings, :desc)
      assert hd(result.players).name == "Neymar Jr"
    end

    test "Given sort_by age Then the youngest come first", %{graph: graph} do
      result = ok!(Players.search(graph, %{sort_by: "age", limit: 5}))
      ages = Enum.map(result.players, & &1.age)

      assert ages == Enum.sort(ages)
    end

    test "Given sort_by value Then the most valuable come first", %{graph: graph} do
      result = ok!(Players.search(graph, %{sort_by: "value", limit: 5}))
      values = Enum.map(result.players, & &1.value_eur)

      assert values == Enum.sort(values, :desc)
    end
  end

  describe "Scenario: player profile" do
    test "Given a name Then ratings, attributes and club come back", %{graph: graph} do
      result = ok!(Players.profile(graph, %{name: "Neymar"}))

      assert result.player.name == "Neymar Jr"
      assert result.player.overall == 92
      assert result.player.club == "Paris Saint-Germain"
      assert length(result.top_skills) == 6
      assert result.club_team == nil
    end

    test "Given a player at a Brazilian club Then the match graph is linked in", %{graph: graph} do
      %{id: id} =
        graph.players
        |> Map.values()
        |> Enum.find(&(&1.club == "Grêmio"))

      result = ok!(Players.profile(graph, %{player_id: id}))

      assert result.club_team.name == "Grêmio"
      assert length(result.club_matches) == 5
      assert length(result.teammates) == 5
    end

    test "Given an unknown player Then suggestions come back", %{graph: graph} do
      assert {:error, {:player_not_found, "Zinedine Zidane", suggestions}} =
               Players.profile(graph, %{name: "Zinedine Zidane"})

      assert length(suggestions) > 0
    end
  end

  describe "Scenario: club squads" do
    test "Given a club with players Then the squad summary comes back", %{graph: graph} do
      result = ok!(Players.club_squad(graph, %{club: "Grêmio"}))

      assert result.size == 20
      assert result.average_overall > 60
      assert result.best_player.overall >= Enum.max(Enum.map(result.players, & &1.overall))
      assert Map.has_key?(result.by_position, :goalkeeper)
      assert length(result.recent_matches) == 5
    end

    test "Given a club the FIFA export leaves out Then the answer says exactly that", %{
      graph: graph
    } do
      assert {:error, {:club_not_in_player_data, "Flamengo", examples}} =
               Players.club_squad(graph, %{club: "Flamengo"})

      assert "Grêmio" in examples
    end

    test "Given no club Then the error says it is required", %{graph: graph} do
      assert {:error, {:missing_argument, :club}} = Players.club_squad(graph, %{})
    end

    test "Given a club nobody has heard of Then it errors instead of crashing", %{graph: graph} do
      assert {:error, {:club_not_found, "Nowhere United", examples}} =
               Players.club_squad(graph, %{club: "Nowhere United"})

      assert examples != []
      assert {:ok, %{total: 0}} = Players.search(graph, %{club: "Nowhere United"})
    end
  end

  describe "Scenario: nationality report" do
    test "Given Brazil Then top players and club spread come back", %{graph: graph} do
      result = ok!(Players.nationality_report(graph, %{nationality: "Brazil", limit: 5}))

      assert result.total == 827
      assert length(result.top_players) == 5
      assert result.at_brazilian_clubs > 100
      assert Enum.all?(result.by_brazilian_club, &(&1.team != nil and &1.count > 0))

      counts = Enum.map(result.by_brazilian_club, & &1.count)
      assert counts == Enum.sort(counts, :desc)
    end

    test "Given no nationality Then Brazil is the default", %{graph: graph} do
      result = ok!(Players.nationality_report(graph, %{}))
      assert result.nationality == "Brazil"
    end
  end
end
