defmodule BrazilianSoccerMcp.QueriesTest do
  use ExUnit.Case, async: true

  import BrazilianSoccerMcp.Fixtures

  alias BrazilianSoccerMcp.Queries

  @matches matches()
  @players players()

  describe "Given a team name with different accents or case" do
    test "When resolved Then it finds the canonical key" do
      assert Queries.resolve_team(@matches, "alpha") == "alpha"
      assert Queries.resolve_team(@matches, "ALPHA") == "alpha"
    end

    test "When the name is unknown Then nil is returned" do
      assert Queries.resolve_team(@matches, "Nowhere FC") == nil
    end
  end

  describe "Given matches between teams" do
    test "When searching by team Then matches are returned most recent first" do
      {:ok, %{total: total, matches: found}} =
        Queries.search_matches(@matches, team: "Alpha", season: 2023)

      assert total == 4

      assert Enum.map(found, & &1.date) == [
               ~D[2023-05-01],
               ~D[2023-04-01],
               ~D[2023-03-15],
               ~D[2023-03-01]
             ]
    end

    test "When searching by team and opponent Then only meetings between them are returned" do
      {:ok, %{total: 2}} = Queries.search_matches(@matches, team: "Alpha", opponent: "Beta")
    end

    test "When restricted to home matches Then away fixtures are excluded" do
      {:ok, %{matches: found}} =
        Queries.search_matches(@matches, team: "Alpha", season: 2023, venue: :home)

      assert Enum.all?(found, &(&1.home_key == "alpha"))
      assert length(found) == 3
    end

    test "When a limit is given Then only that many rows are returned but total is unchanged" do
      {:ok, %{total: 5, matches: found}} =
        Queries.search_matches(@matches, team: "Alpha", limit: 2)

      assert length(found) == 2
    end

    test "When the date range is given Then matches outside it are excluded" do
      {:ok, %{total: total}} =
        Queries.search_matches(@matches,
          team: "Alpha",
          date_from: ~D[2023-03-10],
          date_to: ~D[2023-04-30]
        )

      assert total == 2
    end

    test "When the team is unknown Then an error explains which team" do
      assert {:error, "Unknown team: Nowhere FC"} =
               Queries.search_matches(@matches, team: "Nowhere FC")
    end
  end

  describe "Given Alpha's 2023 results" do
    test "When asked for the team record Then wins, draws, losses, goals and win rate are correct" do
      {:ok, stats} = Queries.team_record(@matches, "Alpha", season: 2023)

      assert %{
               played: 4,
               wins: 2,
               draws: 1,
               losses: 1,
               gf: 7,
               ga: 4,
               gd: 3,
               points: 7,
               win_rate: 50.0
             } = stats
    end

    test "When restricted to away matches Then only away results count" do
      {:ok, stats} = Queries.team_record(@matches, "Alpha", season: 2023, venue: :away)

      assert %{played: 1, losses: 1, wins: 0} = stats
    end

    test "When the team has no matches in the filter Then the record is all zeros" do
      {:ok, stats} = Queries.team_record(@matches, "Alpha", season: 2010)

      assert stats.played == 0
      assert stats.win_rate == 0.0
    end
  end

  describe "Given a head-to-head request" do
    test "When Alpha and Beta meet Then the record is from Alpha's point of view" do
      {:ok, h2h} = Queries.head_to_head(@matches, "Alpha", "Beta")

      assert %{matches: 2, a_wins: 2, b_wins: 0, draws: 0, a_goals: 6, b_goals: 1} = h2h
    end

    test "When the same team is given twice Then an error is returned" do
      assert {:error, _} = Queries.head_to_head(@matches, "Alpha", "Alpha")
    end
  end

  describe "Given the 2023 league season" do
    test "When the standings are requested Then teams are ordered by points" do
      {:ok, table} = Queries.standings(@matches, season: 2023)

      assert Enum.map(table, &{&1.team, &1.points}) == [{"Gamma", 5}, {"Alpha", 4}, {"Beta", 1}]
    end

    test "When no season is given Then standings are refused" do
      assert {:error, _} = Queries.standings(@matches, [])
    end

    test "When the cup is requested Then it is excluded from the Brasileirão table by default" do
      {:ok, table} = Queries.standings(@matches, season: 2023)

      alpha = Enum.find(table, &(&1.team == "Alpha"))
      assert alpha.played == 3
    end
  end

  describe "Given aggregate match data" do
    test "When league statistics are requested Then goals per match and home/draw/away rates are computed" do
      {:ok, stats} = Queries.league_stats(@matches, season: 2023, competition: "Brasileirão")

      assert stats.matches == 4
      assert stats.goals_per_match == 1.75
      assert stats.home_win_rate == 50.0
      assert stats.draw_rate == 50.0
      assert stats.away_win_rate == 0.0
    end

    test "When biggest wins are requested Then draws are skipped and the largest margin comes first" do
      {:ok, [first, second | _]} = Queries.biggest_wins(@matches, [])

      assert {first.home, first.away} == {"Alpha", "Beta"}
      assert first.home_goals - first.away_goals == 4
      assert {second.home, second.away} == {"Gamma", "Alpha"}
    end

    test "When rankings are requested with a minimum games threshold Then teams below it are excluded" do
      {:ok, rows} =
        Queries.team_rankings(@matches, season: 2023, competition: "brasileirao", min_matches: 3)

      assert Enum.map(rows, & &1.team) |> Enum.sort() == ["Alpha", "Gamma"]
    end

    test "When ranking by goals scored Then the highest scorer is first" do
      {:ok, [top | _]} = Queries.team_rankings(@matches, metric: :gf, min_matches: 1)

      assert top.gf >= 3
    end
  end

  describe "Given the player data" do
    test "When searching for Brazilian players above 80 Then only matching players return, best first" do
      {:ok, found} = Queries.search_players(@players, nationality: "brazil", min_overall: 80)

      assert Enum.map(found, & &1.name) == ["Ana Silva", "Bruno Costa"]
    end

    test "When searching by name fragment Then matching is case and accent insensitive" do
      {:ok, [player]} = Queries.search_players(@players, name: "CARLOS")

      assert player.name == "Carlos Ruiz"
    end

    test "When searching by club Then only that club's players return" do
      {:ok, found} = Queries.search_players(@players, club: "Alpha")

      assert length(found) == 2
    end

    test "When summarising Brazilian players by club Then clubs in the match data are grouped" do
      {:ok, rows} = Queries.club_summary(@players, @matches)

      assert [
               %{club: "Alpha", squad_size: 2, avg_overall: 82.5, best: %{name: "Ana Silva"}},
               %{club: "Gamma"}
             ] =
               rows
    end
  end

  describe "Given a team that exists in both match and player data" do
    test "When the team overview is requested Then the record and squad are combined" do
      {:ok, overview} = Queries.team_overview(@matches, @players, "Alpha")

      assert overview.record.played == 5
      assert overview.squad_size == 2
      assert overview.avg_overall == 82.5
      assert Enum.map(overview.top, & &1.name) == ["Ana Silva", "Bruno Costa"]
    end
  end
end
