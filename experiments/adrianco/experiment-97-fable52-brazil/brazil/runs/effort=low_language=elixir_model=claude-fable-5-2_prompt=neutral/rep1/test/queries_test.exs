defmodule BrazilianSoccer.QueriesTest do
  @moduledoc "BDD-style scenarios (Given the loaded data / When a query runs / Then ...)."
  use ExUnit.Case, async: true

  alias BrazilianSoccer.{Data, Queries}

  setup_all do
    {:ok, data: Data.get()}
  end

  describe "Feature: match queries" do
    test "Scenario: find matches between two teams", %{data: d} do
      # When I search for matches between Flamengo and Fluminense
      {:ok, ms} = Queries.matches(d, team: "Flamengo", opponent: "Fluminense")

      # Then I receive a list of matches, each with date, scores and competition
      assert length(ms) == 44

      for m <- ms do
        assert Enum.sort([m.home, m.away]) == ["flamengo", "fluminense"]
        assert %Date{} = m.date
        assert m.home_goals >= 0 and m.away_goals >= 0
        assert m.competition in Data.competitions()
      end

      # And they are ordered newest first
      assert ms == Enum.sort_by(ms, &Date.to_gregorian_days(&1.date), :desc)
      # And the same result is returned whichever spelling is used
      assert {:ok, ^ms} = Queries.matches(d, team: "Fluminense-RJ", opponent: "flamengo - RJ")
    end

    test "Scenario: filter by team, season, venue and competition", %{data: d} do
      {:ok, ms} = Queries.matches(d, team: "Palmeiras", season: 2019, competition: "Brasileirão")
      assert length(ms) == 38

      {:ok, home} =
        Queries.matches(d, team: "Palmeiras", season: 2019, competition: "Serie A", venue: "home")

      assert length(home) == 19
      assert Enum.all?(home, &(&1.home == "palmeiras"))

      {:ok, all} = Queries.matches(d, team: "Palmeiras", season: 2018)

      assert all |> Enum.map(& &1.competition) |> Enum.uniq() |> Enum.sort() ==
               ["Brasileirão Série A", "Copa Libertadores", "Copa do Brasil"]
    end

    test "Scenario: filter by date range in either date format", %{data: d} do
      {:ok, ms} = Queries.matches(d, date_from: "01/05/2019", date_to: "2019-05-31")
      assert ms != []
      assert Enum.all?(ms, &(&1.date.year == 2019 and &1.date.month == 5))
      assert {:error, _} = Queries.matches(d, date_from: "yesterday")
    end

    test "Scenario: find cup finals", %{data: d} do
      {:ok, cup} = Queries.matches(d, competition: "Copa do Brasil", stage: "final")
      assert length(cup) == 24
      assert Enum.sort(Enum.uniq(Enum.map(cup, & &1.season))) == Enum.to_list(2012..2023)

      {:ok, [m]} = Queries.matches(d, competition: "Libertadores", stage: "final", season: 2019)

      assert {m.home_name, m.home_goals, m.away_goals, m.away_name} ==
               {"Flamengo", 2, 1, "River Plate"}
    end

    test "Scenario: most recent meeting between two teams", %{data: d} do
      {:ok, [last | _]} = Queries.matches(d, team: "Flamengo", opponent: "Corinthians")
      assert last.date == ~D[2023-10-08]
    end

    test "Scenario: unknown team or competition is reported", %{data: d} do
      assert {:error, msg} = Queries.matches(d, team: "Nowhere United")
      assert msg =~ "Team not found"
      assert {:error, _} = Queries.matches(d, competition: "Premier League")
    end
  end

  describe "Feature: team queries" do
    test "Scenario: team statistics for a season", %{data: d} do
      {:ok, s} = Queries.team_stats(d, "Palmeiras", season: 2019, competition: "Brasileirão")

      assert %{
               matches: 38,
               wins: 21,
               draws: 11,
               losses: 6,
               goals_for: 61,
               goals_against: 32,
               points: 74
             } = s.overall

      assert s.home.matches + s.away.matches == 38
    end

    test "Scenario: home record", %{data: d} do
      {:ok, s} =
        Queries.team_stats(d, "Corinthians",
          season: 2022,
          competition: "Brasileirão",
          venue: "home"
        )

      assert %{
               matches: 19,
               wins: 12,
               draws: 4,
               losses: 3,
               goals_for: 24,
               goals_against: 11,
               win_rate: 63.2
             } = s.overall
    end

    test "Scenario: head-to-head comparison", %{data: d} do
      {:ok, h} = Queries.head_to_head(d, "Palmeiras", "Santos")
      assert h.total == h.a_wins + h.b_wins + h.draws
      assert {h.total, h.a_wins, h.b_wins, h.draws} == {41, 17, 16, 8}

      # symmetric when the teams are swapped
      {:ok, r} = Queries.head_to_head(d, "Santos", "Palmeiras")
      assert {r.a_wins, r.b_wins, r.draws} == {h.b_wins, h.a_wins, h.draws}
    end

    test "Scenario: cross-file team profile (matches + players)", %{data: d} do
      {:ok, p} = Queries.team_profile(d, "Gremio")
      assert p.team == "Grêmio"

      assert Enum.map(p.competitions, &elem(&1, 0)) |> Enum.sort() ==
               [
                 "Brasileirão Série A",
                 "Brasileirão Série B",
                 "Copa Libertadores",
                 "Copa do Brasil"
               ]

      assert length(p.squad) == 20
      assert Enum.all?(p.squad, &(&1.club == "Grêmio"))
    end
  end

  describe "Feature: competition queries" do
    test "Scenario: league standings and champion", %{data: d} do
      {:ok, s} = Queries.standings(d, "Brasileirão", 2019)
      assert s.complete
      assert length(s.rows) == 20
      [first, second, third | _] = s.rows

      assert %{team: "Flamengo", points: 90, wins: 28, draws: 6, losses: 4, note: "Champion"} =
               first

      assert %{team: "Santos", points: 74, wins: 22} = second
      assert %{team: "Palmeiras", points: 74, wins: 21} = third
    end

    test "Scenario: relegated teams", %{data: d} do
      {:ok, s} = Queries.standings(d, "Serie A", 2020)
      relegated = for r <- s.rows, r.note == "Relegated", do: r.team
      assert relegated == ["Vasco", "Goiás", "Coritiba", "Botafogo-RJ"]
    end

    test "Scenario: champions of other seasons and divisions", %{data: d} do
      for {season, champion} <- [
            {2003, "Cruzeiro"},
            {2012, "Fluminense"},
            {2014, "Cruzeiro"},
            {2018, "Palmeiras"},
            {2022, "Palmeiras"}
          ] do
        {:ok, s} = Queries.standings(d, "Serie A", season)
        assert hd(s.rows).team == champion, "#{season}"
        assert hd(s.rows).note == "Champion"
      end

      {:ok, b} = Queries.standings(d, "Serie B", 2019)
      assert hd(b.rows).team == "Bragantino"
    end

    test "Scenario: incomplete season is not given a champion", %{data: d} do
      {:ok, s} = Queries.standings(d, "Serie A", 2023)
      refute s.complete
      assert Enum.all?(s.rows, &(&1.note == nil))
      assert {:error, _} = Queries.standings(d, "Serie A", 1990)
      assert {:error, _} = Queries.standings(d, "Libertadores", 2019)
    end

    test "Scenario: knockout bracket", %{data: d} do
      {:ok, b} = Queries.bracket(d, "Libertadores", 2019)

      assert Enum.map(b.rounds, fn {l, ms} -> {l, length(ms)} end) ==
               [
                 {"group stage", 96},
                 {"round of 16", 16},
                 {"quarterfinals", 8},
                 {"semifinals", 4},
                 {"final", 1}
               ]

      assert b.champion == "Flamengo"

      {:ok, cup} = Queries.bracket(d, "Copa do Brasil", 2019)
      assert cup.champion == "Athletico-PR"
    end
  end

  describe "Feature: statistical analysis" do
    test "Scenario: average goals per match and home win rate", %{data: d} do
      {:ok, s} = Queries.summary(d, competition: "Brasileirão", season: 2019)

      assert %{
               matches: 380,
               goals: 876,
               avg_goals: 2.31,
               home_wins: 184,
               draws: 98,
               away_wins: 98,
               home_win_rate: 48.4
             } = s

      {:ok, all} = Queries.summary(d, competition: "Brasileirão")
      assert all.avg_goals > 2.0 and all.avg_goals < 3.0
      assert all.home_win_rate > all.away_win_rate
    end

    test "Scenario: best home and away records", %{data: d} do
      {:ok, home} = Queries.rankings(d, venue: "home", competition: "Serie A")
      assert %{team: "Grêmio", win_rate: 59.1} = hd(home.rows)
      assert Enum.all?(home.rows, &(&1.matches >= home.min_matches))

      {:ok, away} = Queries.rankings(d, venue: "away", competition: "Serie A", season: 2019)
      assert hd(away.rows).team == "Flamengo"
      assert {:error, _} = Queries.rankings(d, metric: "vibes")
    end

    test "Scenario: most goals in a season", %{data: d} do
      {:ok, r} = Queries.rankings(d, competition: "Serie A", season: 2019, metric: "goals_for")
      assert %{team: "Flamengo", goals_for: 86} = hd(r.rows)
    end

    test "Scenario: biggest wins", %{data: d} do
      {:ok, [top | _] = wins} = Queries.biggest_wins(d, [competition: "Serie A"], 5)
      assert length(wins) == 5

      assert {top.home_name, top.home_goals, top.away_goals, top.away_name} ==
               {"São Paulo", 7, 0, "Paysandu"}

      margins = Enum.map(wins, &abs(&1.home_goals - &1.away_goals))
      assert margins == Enum.sort(margins, :desc)
    end

    test "Scenario: derbies in a season", %{data: d} do
      {:ok, list} = Queries.derbies(d, season: 2023)
      assert length(list) == 37

      assert Enum.any?(list, fn {nick, m} ->
               nick == "Fla-Flu" and Enum.sort([m.home, m.away]) == ["flamengo", "fluminense"]
             end)

      assert Enum.all?(list, fn {_, m} -> m.season == 2023 end)
    end
  end

  describe "Feature: player queries" do
    test "Scenario: search by name (accent-insensitive)", %{data: d} do
      {:ok, [p | _]} = Queries.players(d, name: "neymar")

      assert %{
               name: "Neymar Jr",
               overall: 92,
               position: "LW",
               club: "Paris Saint-Germain",
               nationality: "Brazil"
             } = p

      assert p.attributes["Dribbling"] == 96
      {:ok, ps} = Queries.players(d, name: "gabriel jesus")
      assert Enum.map(ps, & &1.name) == ["Gabriel Jesus"]
    end

    test "Scenario: Brazilian players sorted by rating", %{data: d} do
      {:ok, ps} = Queries.players(d, nationality: "Brazilian")
      assert length(ps) == 827
      assert Enum.map(Enum.take(ps, 3), & &1.name) == ["Neymar Jr", "Casemiro", "Coutinho"]
      assert Enum.map(ps, & &1.overall) == Enum.sort(Enum.map(ps, & &1.overall), :desc)
    end

    test "Scenario: filter by club and position", %{data: d} do
      {:ok, ps} = Queries.players(d, club: "Santos", position: "forward")
      assert ps != []
      assert Enum.all?(ps, &(&1.club == "Santos" and &1.position in ~w(ST CF LF RF LS RS LW RW)))

      # club name variation: "Atlético-MG" finds FIFA's "Atlético Mineiro"
      {:ok, galo} = Queries.players(d, club: "Atlético-MG")
      assert length(galo) == 20
      assert Enum.all?(galo, &(&1.club == "Atlético Mineiro"))

      {:ok, gks} = Queries.players(d, position: "GK", min_overall: 89)
      assert Enum.all?(gks, &(&1.position == "GK" and &1.overall >= 89))
      assert "De Gea" in Enum.map(gks, & &1.name)
    end

    test "Scenario: players at Brazilian clubs", %{data: d} do
      rows = Queries.brazilian_club_summary(d, nationality: "Brazil")
      assert length(rows) == 15
      assert Enum.all?(rows, &(&1.players > 0 and &1.avg_overall > 50))
      assert "Grêmio" in Enum.map(rows, & &1.club)
      # European namesakes are not mistaken for Brazilian clubs
      refute "Boavista FC" in Enum.map(rows, & &1.club)
    end
  end

  describe "Feature: performance" do
    test "Scenario: lookups and aggregates are fast once loaded", %{data: d} do
      {t1, _} = :timer.tc(fn -> Queries.matches(d, team: "Flamengo", opponent: "Corinthians") end)
      {t2, _} = :timer.tc(fn -> Queries.rankings(d, venue: "away") end)
      {t3, _} = :timer.tc(fn -> Queries.players(d, nationality: "Brazil") end)
      assert t1 < 2_000_000
      assert t2 < 5_000_000
      assert t3 < 2_000_000
    end
  end
end

defmodule BrazilianSoccer.ColdLoadTest do
  use ExUnit.Case, async: false

  alias BrazilianSoccer.Data

  describe "Feature: performance" do
    test "Scenario: a cold load of all files stays within the aggregate budget" do
      {t, data} = :timer.tc(fn -> Data.load!() end)
      assert length(data.matches) > 16_000
      assert t < 10_000_000, "loading took #{div(t, 1000)} ms"
    end
  end
end
