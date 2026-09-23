defmodule BrSoccer.FeaturesTest do
  @moduledoc "BDD-style scenarios (Given/When/Then) from the specification."
  use ExUnit.Case, async: true
  alias BrSoccer.{Data, Query, Tools}

  defp tool(name, args) do
    assert {:ok, text} = Tools.call(name, args)
    text
  end

  describe "Feature: Data coverage" do
    test "all six CSV files are loaded and queryable" do
      sources = Data.matches() |> Enum.map(& &1.source) |> Enum.uniq() |> Enum.sort()

      assert sources == ~w(BR-Football-Dataset.csv Brasileirao_Matches.csv Brazilian_Cup_Matches.csv
                           Libertadores_Matches.csv novo_campeonato_brasileiro.csv)

      assert length(Data.players()) == 18_207
      assert Enum.all?(Data.competitions(), fn c -> Enum.any?(Data.matches(), &(&1.competition == c)) end)
    end

    test "UTF-8 names survive loading" do
      assert Enum.any?(Data.matches(), &(&1.home == "Grêmio"))
    end

    test "league seasons have one fixture per pairing after cross-file dedup" do
      # 2016 additionally contains one lower-division game mislabelled "Serie A" in BR-Football-Dataset.
      for s <- Enum.to_list(2006..2022) -- [2016], do: assert(length(Query.matches(season: s, competition: "serie_a")) in 379..380)
    end
  end

  describe "Feature: Match Queries" do
    test "Scenario: Find matches between two teams" do
      # Given the match data is loaded / When I search Flamengo vs Fluminense
      ms = Query.matches(team: "Flamengo", opponent: "Fluminense")
      # Then I receive a list of matches, each with date, scores and competition
      assert length(ms) > 20

      for m <- ms do
        assert %Date{} = m.date
        assert m.competition in Data.competitions()
        assert m.home_key in ["flamengo", "fluminense"] and m.away_key in ["flamengo", "fluminense"]
      end

      assert tool("head_to_head", %{"team_a" => "Flamengo", "team_b" => "Fluminense"}) =~ ~r/Fla-Flu.*Head-to-head in dataset/s
    end

    test "matches by team and season, across competitions" do
      text = tool("search_matches", %{"team" => "Palmeiras", "season" => 2023, "limit" => 100})
      assert text =~ "Palmeiras"
      assert Query.matches(team: "Palmeiras", season: 2023) |> Enum.all?(&(&1.season == 2023))
    end

    test "matches by date range and venue" do
      ms = Query.matches(team: "Santos", venue: "home", date_from: "2015-01-01", date_to: "31/12/2015")
      assert ms != []
      assert Enum.all?(ms, &(&1.home_key == "santos" and &1.date.year == 2015))
    end

    test "Copa do Brasil and Libertadores finals" do
      assert tool("cup_finals", %{}) =~ "Copa do Brasil"
      text = tool("cup_finals", %{"competition" => "libertadores", "season" => 2019})
      assert text =~ "Flamengo 2-1 River Plate"
    end

    test "most recent Flamengo vs Corinthians match" do
      [m | _] = Query.matches(team: "Flamengo", opponent: "Corinthians")
      assert is_integer(m.home_goal) and is_integer(m.away_goal)
    end
  end

  describe "Feature: Team Queries" do
    test "Scenario: Get team statistics" do
      r = Query.team_record("Palmeiras", season: 2023)
      assert r.played > 0
      assert r.wins + r.draws + r.losses == r.played
      assert r.gf > 0 and r.ga > 0
    end

    test "Corinthians home record 2022" do
      text = tool("team_stats", %{"team" => "Corinthians", "season" => 2022, "venue" => "home", "competition" => "Brasileirão"})
      assert text =~ "Corinthians home record (2022 Brasileirão Série A)"
      assert text =~ "Win rate:"
    end

    test "competitions Palmeiras played in" do
      comps = Query.team_competitions("Palmeiras") |> Enum.map(&elem(&1, 0))
      assert :serie_a in comps and :copa_do_brasil in comps and :libertadores in comps
    end

    test "top scoring team in Serie A season" do
      assert tool("top_scoring_teams", %{"season" => 2019, "limit" => 1}) =~ "1. Flamengo"
    end
  end

  describe "Feature: Competition Queries" do
    test "2019 Brasileirão champion is Flamengo with 38 matches played" do
      [first | _] = table = Query.standings(2019)
      assert first.team == "flamengo"
      assert first.played == 38
      assert length(table) == 20
      assert tool("standings", %{"season" => 2019}) =~ "1. Flamengo - 90 pts (28W, 6D, 4L"
    end

    test "relegated teams are flagged" do
      text = tool("standings", %{"season" => 2020})
      assert length(Regex.scan(~r/Relegated/, text)) == 4
    end

    test "compare two seasons" do
      text = tool("compare_seasons", %{"season_a" => 2018, "season_b" => 2019})
      assert text =~ "2018 Brasileirão" and text =~ "Champion: Flamengo"
    end
  end

  describe "Feature: Statistical Analysis" do
    test "average goals and home win rate" do
      s = Query.summary(competition: "serie_a")
      assert s.avg_goals > 2.0 and s.avg_goals < 3.0
      assert s.home_win_pct > 40
      assert tool("competition_stats", %{"competition" => "brasileirao"}) =~ "Average goals per match"
    end

    test "biggest wins sorted by margin" do
      [a, b | _] = Query.biggest_wins(limit: 5)
      assert abs(a.home_goal - a.away_goal) >= abs(b.home_goal - b.away_goal)
    end

    test "best away record" do
      [best | _] = Query.best_records(venue: "away", competition: "serie_a", min_matches: 50)
      assert best.played >= 50
      assert tool("best_records", %{"venue" => "away"}) =~ "Best away records"
    end

    test "derbies in a season" do
      text = tool("derbies", %{"season" => 2019})
      assert text =~ "Fla-Flu" and text =~ "Grenal"
    end
  end

  describe "Feature: Player Queries" do
    test "Brazilian players sorted by rating" do
      [top | _] = ps = Query.players(nationality: "Brazil")
      assert length(ps) > 500
      assert top.name == "Neymar Jr"
      assert tool("search_players", %{"nationality" => "Brazil", "limit" => 3}) =~ "1. Neymar Jr - Overall: 92"
    end

    test "players at a Brazilian club and position groups" do
      ps = Query.players(club: "Grêmio")
      assert ps != [] and Enum.all?(ps, &(&1.club == "Grêmio"))
      fwd = Query.players(club: "Santos", position: "forward")
      assert Enum.all?(fwd, &(&1.position in ~w(ST CF LF RF LW RW LS RS)))
    end

    test "search by name with accents" do
      assert [%{name: "Neymar Jr"} | _] = Query.players(name: "neymar")
      assert tool("search_players", %{"name" => "Casemiro"}) =~ "Skills:"
    end

    test "Brazilian players grouped by club" do
      assert tool("players_by_club", %{"nationality" => "Brazil"}) =~ "avg rating"
    end
  end

  describe "Feature: Cross-file queries" do
    test "club profile combines match and player data" do
      text = tool("club_profile", %{"team" => "Cruzeiro"})
      assert text =~ "Matches:" and text =~ "FIFA squad" and text =~ "Overall"
    end
  end

  describe "Feature: Performance" do
    test "aggregate queries run well under 5s and lookups under 2s" do
      {us, _} = :timer.tc(fn -> Query.best_records(venue: "home") end)
      assert us < 5_000_000
      {us, _} = :timer.tc(fn -> Query.players(name: "Gabriel") end)
      assert us < 2_000_000
    end
  end

  test "unknown competition returns an error" do
    assert {:error, _} = Tools.call("search_matches", %{"competition" => "premier league"})
  end
end
