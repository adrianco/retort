defmodule BrazilianSoccerMcp.QueriesTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccerMcp.Queries

  describe "Given the match data is loaded, when I search for matches between two teams" do
    test "then I receive a list of matches with date, scores, and competition" do
      result = Queries.head_to_head("Flamengo", "Fluminense")

      assert length(result.matches) > 20

      for m <- result.matches do
        assert %Date{} = m.date
        assert m.competition in [:brasileirao, :copa_do_brasil, :libertadores, :serie_b, :serie_c]
        assert m.home_key in ["flamengo-rj", "fluminense-rj"]
        assert m.away_key in ["flamengo-rj", "fluminense-rj"]
      end

      s = result.summary
      assert s.team1_wins + s.team2_wins + s.draws <= length(result.matches)
      assert s.team1_wins > 0 and s.team2_wins > 0
    end
  end

  describe "Given the match data is loaded, when I request team statistics" do
    test "then I receive wins, losses, draws, and goals for Palmeiras in 2023" do
      %{stats: s} = Queries.team_stats("Palmeiras", season: 2023)

      assert s.played > 30
      assert s.wins + s.draws + s.losses == s.played
      assert s.goals_for > 0 and s.goals_against > 0
    end

    test "then venue filtering yields a 19-game Série A home record" do
      %{stats: s} =
        Queries.team_stats("Corinthians", season: 2022, competition: "Brasileirão", venue: :home)

      assert s.played == 19
      assert s.wins + s.draws + s.losses == 19
    end
  end

  describe "Given team name variations, when I search by any spelling" do
    test "then 'Athletico-PR', 'Atlético - PR' and 'Atletico Paranaense' find the same team" do
      keys = Queries.find_team_keys("Athletico-PR")
      assert keys == Queries.find_team_keys("Atlético - PR")
      assert keys == Queries.find_team_keys("Atletico Paranaense")
      assert MapSet.member?(keys, "athletico-pr")
    end

    test "then an ambiguous name like 'América' resolves to all namesakes" do
      keys = Queries.find_team_keys("América")
      assert MapSet.member?(keys, "america-mg")
      assert MapSet.member?(keys, "america-rn")
    end

    test "then an unknown name resolves to no teams" do
      assert MapSet.size(Queries.find_team_keys("Real Madrid CF Basketball")) == 0
    end
  end

  describe "Given match filters, when I search" do
    test "then competition and season filters combine" do
      matches =
        Queries.search_matches(team: "Palmeiras", competition: "Libertadores", season: 2021)

      assert matches != []
      assert Enum.all?(matches, &(&1.competition == :libertadores and &1.season == 2021))
    end

    test "then date ranges are inclusive and sorted most recent first" do
      matches =
        Queries.search_matches(
          team: "Santos",
          date_from: ~D[2019-01-01],
          date_to: ~D[2019-12-31]
        )

      assert matches != []
      assert Enum.all?(matches, &(&1.date.year == 2019))
      dates = Enum.map(matches, & &1.date)
      assert dates == Enum.sort(dates, {:desc, Date})
    end

    test "then stage 'final' finds Libertadores finals but not semifinals" do
      matches = Queries.search_matches(competition: "Libertadores", stage: "final")
      assert matches != []
      assert Enum.all?(matches, &(&1.stage == "final"))
    end
  end

  describe "Given match results, when I compute standings" do
    test "then the 2019 Brasileirão table matches the official result" do
      [first | rest] = Queries.standings(2019)

      assert first.team == "Flamengo"
      assert first.points == 90
      assert first.wins == 28
      assert first.draws == 6
      assert first.losses == 4

      # 20 teams, each with 38 played
      assert length([first | rest]) == 20
      assert Enum.all?([first | rest], &(&1.played == 38))

      # Santos finished 2nd on 74 points
      second = hd(rest)
      assert second.team == "Santos"
      assert second.points == 74
    end

    test "then a pre-2012 season is computed from the historical file" do
      [first | _] = Queries.standings(2003)
      assert first.team == "Cruzeiro"
      assert first.points > 90
    end
  end

  describe "Given the FIFA data is loaded, when I search players" do
    test "then name search is accent- and case-insensitive" do
      assert [p] = Queries.search_players(name: "neymar")
      assert p.name == "Neymar Jr"
      assert p.overall == 92
      assert p.position == "LW"
    end

    test "then Brazilians can be filtered and ranked" do
      players = Queries.search_players(nationality: "Brazil", limit: 5)
      assert length(players) == 5
      assert hd(players).name == "Neymar Jr"
      assert Enum.all?(players, &(&1.nationality == "Brazil"))

      overalls = Enum.map(players, & &1.overall)
      assert overalls == Enum.sort(overalls, :desc)
    end

    test "then club and position filters work together" do
      players = Queries.search_players(club: "Santos", nationality: "Brazil", position: "forward")
      assert players != []
      assert Enum.all?(players, &String.contains?(&1.club, "Santos"))
      assert Enum.all?(players, &(&1.position in ~w(ST CF LW RW LS RS LF RF)))
    end

    test "then min_overall bounds the results" do
      players = Queries.search_players(nationality: "Brazil", min_overall: 85, limit: 100)
      assert players != []
      assert Enum.all?(players, &(&1.overall >= 85))
    end
  end

  describe "Given all match data, when I compute aggregate statistics" do
    test "then biggest wins have the largest margins first" do
      wins = Queries.biggest_wins(limit: 5)
      margins = Enum.map(wins, &abs(&1.home_goal - &1.away_goal))
      assert margins == Enum.sort(margins, :desc)
      assert hd(margins) >= 6
    end

    test "then competition stats include averages and rates" do
      stats = Queries.competition_stats(competition: "Brasileirão")

      assert stats.matches > 8000
      assert stats.avg_goals > 1.5 and stats.avg_goals < 4.0
      # Home advantage is a robust phenomenon in Brazilian soccer
      assert stats.home_win_rate > stats.away_win_rate

      assert_in_delta stats.home_win_rate + stats.draw_rate + stats.away_win_rate, 100.0, 0.5
    end
  end
end
