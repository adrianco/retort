defmodule BrazilianSoccer.QueriesTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.{Match, Players, Queries, Store}

  setup_all do
    {:ok, data: Store.data()}
  end

  describe "Feature: data loading" do
    test "Given the data directory, then all six CSV files are loaded", %{data: data} do
      assert data.file_counts == %{
               "Brasileirao_Matches.csv" => 4180,
               "Brazilian_Cup_Matches.csv" => 1337,
               # one row has no date ("NA") and is skipped
               "Libertadores_Matches.csv" => 1254,
               "BR-Football-Dataset.csv" => 10296,
               "novo_campeonato_brasileiro.csv" => 6886,
               "fifa_data.csv" => 18207
             }
    end

    test "every source file contributes matches, and overlapping fixtures are merged", %{
      data: data
    } do
      sources = data.matches |> Enum.flat_map(& &1.sources) |> Enum.frequencies()
      assert map_size(sources) == 5
      assert length(data.matches) < 4180 + 1337 + 1254 + 10296 + 6886

      # A 2019 Série A fixture appears in three of the files.
      [m] =
        Queries.matches(%{
          team: "Flamengo",
          opponent: "Avaí",
          venue: "home",
          season: 2019,
          competition: "Serie A"
        })

      assert length(m.sources) == 3
      assert {m.home_goals, m.away_goals} == {6, 1}
      assert m.arena != nil and m.round != nil and m.stats != nil
    end

    test "UTF-8 names survive loading", %{data: data} do
      names = data.matches |> Enum.flat_map(&[&1.home, &1.away]) |> MapSet.new()
      for n <- ["São Paulo", "Grêmio", "Avaí", "Ceará", "Goiás"], do: assert(n in names)
    end
  end

  describe "Feature: match queries" do
    test "Scenario: find matches between two teams" do
      # When I search for matches between Flamengo and Fluminense
      ms = Queries.matches(%{team: "Flamengo", opponent: "Fluminense"})
      # Then I receive a list of matches, each with date, scores and competition
      assert length(ms) > 30

      for m <- ms do
        assert %Date{} = m.date
        assert is_binary(m.competition)
        assert Enum.sort([m.home, m.away]) == ["Flamengo", "Fluminense"]
      end

      assert Enum.all?(Enum.filter(ms, &Match.played?/1), &is_integer(&1.home_goals))
      # newest first
      assert ms == Enum.sort_by(ms, &Date.to_erl(&1.date), :desc)
    end

    test "Scenario: name variations give identical results" do
      a = Queries.matches(%{team: "Sao Paulo-SP", opponent: "Gremio"})
      b = Queries.matches(%{team: "São Paulo", opponent: "Grêmio - RS"})
      assert a == b and a != []
    end

    test "Scenario: filter by season, competition, venue and date range" do
      ms = Queries.matches(%{team: "Palmeiras", season: 2023})
      assert ms != []
      assert Enum.all?(ms, &(&1.season == 2023))

      home =
        Queries.matches(%{
          team: "Corinthians",
          season: 2022,
          competition: "Brasileirão",
          venue: "home"
        })

      assert length(home) == 19
      assert Enum.all?(home, &(&1.home == "Corinthians"))

      ranged =
        Queries.matches(%{date_from: "01/05/2019", date_to: "2019-05-31", competition: "Serie A"})

      assert ranged != []
      assert Enum.all?(ranged, &(&1.date.year == 2019 and &1.date.month == 5))
    end

    test "Scenario: each competition is searchable" do
      for c <- ["Brasileirão", "Copa do Brasil", "Libertadores", "Serie B", "Serie C"] do
        assert Queries.matches(%{competition: c}) != [], c
      end

      finals = Queries.matches(%{competition: "Copa do Brasil", stage: "final"})

      assert Enum.any?(
               finals,
               &(&1.season == 2019 and &1.home == "Athletico Paranaense" and
                   &1.away == "Internacional")
             )

      assert Enum.all?(finals, &(&1.stage == "final"))

      lib = Queries.matches(%{competition: "Libertadores", stage: "final", season: 2019})
      assert [%{home: "Flamengo", away: "River Plate", home_goals: 2, away_goals: 1}] = lib
    end

    test "Scenario: the same club name in another state is a different team" do
      ms = Queries.matches(%{team: "Flamengo"})
      refute Enum.any?(ms, &(&1.home == "Flamengo-PI" or &1.away == "Flamengo-PI"))
      assert Queries.matches(%{team: "Flamengo - PI"}) != []
    end

    test "Scenario: unknown team returns no matches" do
      assert Queries.matches(%{team: "Nonexistent United"}) == []
    end
  end

  describe "Feature: team queries" do
    test "Scenario: get team statistics for a season" do
      s = Queries.team_stats("Palmeiras", %{season: 2022, competition: "Serie A"})
      assert s.overall.matches == 38
      assert s.overall.wins + s.overall.draws + s.overall.losses == 38
      assert s.home.matches == 19 and s.away.matches == 19
      assert s.overall.points == 81
      assert s.overall.goals_for == s.home.goals_for + s.away.goals_for
    end

    test "Scenario: head-to-head records are consistent from both sides" do
      h = Queries.head_to_head("Palmeiras", "Santos")
      assert h.derby == "Clássico da Saudade"
      assert h.record_a.matches == h.record_b.matches
      assert h.record_a.wins == h.record_b.losses
      assert h.record_a.draws == h.record_b.draws
      assert h.record_a.goals_for == h.record_b.goals_against
      assert h.record_a.matches > 20
    end

    test "Scenario: competitions a team has played in" do
      comps = "Palmeiras" |> Queries.team_competitions() |> Enum.map(& &1.competition)
      assert "Brasileirão Série A" in comps
      assert "Copa do Brasil" in comps
      assert "Copa Libertadores" in comps
    end
  end

  describe "Feature: competition queries" do
    test "Scenario: 2019 Brasileirão standings match the real table" do
      st = Queries.standings(2019)
      assert st.complete
      assert length(st.rows) == 20

      assert [
               %{team: "Flamengo", points: 90, wins: 28, draws: 6, losses: 4, note: "Champion"},
               %{team: "Santos", points: 74, wins: 22, draws: 8, losses: 8},
               %{team: "Palmeiras", points: 74, wins: 21, draws: 11, losses: 6} | _
             ] = st.rows

      relegated = st.rows |> Enum.filter(&(&1.note == "Relegated")) |> Enum.map(& &1.team)
      assert relegated == ["Cruzeiro", "CSA", "Chapecoense", "Avaí"]
    end

    test "Scenario: champions of every complete Série A season" do
      expected = %{
        2003 => "Cruzeiro",
        2004 => "Santos",
        2005 => "Corinthians",
        2006 => "São Paulo",
        2009 => "Flamengo",
        2012 => "Fluminense",
        2015 => "Corinthians",
        2016 => "Palmeiras",
        2018 => "Palmeiras",
        2020 => "Flamengo",
        2021 => "Atlético Mineiro",
        2022 => "Palmeiras"
      }

      for {season, champion} <- expected do
        st = Queries.standings(season)
        assert st.complete, "season #{season} should be complete"
        assert hd(st.rows).team == champion
        assert Enum.all?(st.rows, &(&1.matches == (length(st.rows) - 1) * 2))
      end
    end

    test "Scenario: relegated teams in 2020" do
      relegated =
        Queries.standings(2020).rows
        |> Enum.filter(&(&1.note == "Relegated"))
        |> Enum.map(& &1.team)

      assert Enum.sort(relegated) == ["Botafogo", "Coritiba", "Goiás", "Vasco da Gama"]
    end
  end

  describe "Feature: statistical analysis" do
    test "Scenario: average goals and home win rate" do
      s = Queries.summary(%{competition: "Brasileirão"})
      assert s.matches > 7000
      assert s.goals_per_match > 2.0 and s.goals_per_match < 3.2
      assert s.home_win_rate > s.away_win_rate
      assert s.home_wins + s.away_wins + s.draws == s.matches
      assert_in_delta s.home_win_rate + s.away_win_rate + s.draw_rate, 100.0, 0.2
    end

    test "Scenario: biggest wins are ordered by margin" do
      ms = Queries.biggest_wins(%{}, 10)
      margins = Enum.map(ms, &abs(&1.home_goals - &1.away_goals))
      assert length(ms) == 10
      assert margins == Enum.sort(margins, :desc)
      assert hd(margins) >= 7
    end

    test "Scenario: best home and away records" do
      [best | _] =
        home = Queries.rankings(%{venue: "home", competition: "Serie A"}, min_matches: 100)

      rates = Enum.map(home, &(&1.wins / &1.matches))
      assert rates == Enum.sort(rates, :desc)
      assert best.win_rate > 50.0

      [top | _] = Queries.rankings(%{season: 2019, competition: "Serie A"}, sort_by: "goals_for")
      assert top.team == "Flamengo" and top.goals_for == 86
    end

    test "Scenario: derbies in a season" do
      ds = Queries.derbies(%{season: 2023})
      assert ds != []
      assert Enum.any?(ds, fn {name, _} -> name == "Fla-Flu" end)
      assert Enum.all?(ds, fn {_, m} -> m.season == 2023 end)
    end

    test "Scenario: compare the 2018 and 2019 seasons" do
      [a, b] = Queries.compare_seasons(2018, 2019)
      assert a.season == 2018 and b.season == 2019
      assert a.summary.matches == 380 and b.summary.matches == 380
      assert hd(a.top).team == "Palmeiras" and hd(b.top).team == "Flamengo"
    end
  end

  describe "Feature: player queries" do
    test "Scenario: search by name, ignoring accents and case" do
      assert [%{name: "Neymar Jr", nationality: "Brazil", overall: 92, position: "LW"} | _] =
               Players.search(%{name: "neymar"})

      assert Players.search(%{name: "DORIA"}) |> Enum.any?(&(&1.name == "Dória"))
    end

    test "Scenario: Brazilian players sorted by rating" do
      ps = Players.search(%{nationality: "Brazil"})
      assert length(ps) > 800
      assert hd(ps).name == "Neymar Jr"
      overall = Enum.map(ps, & &1.overall)
      assert overall == Enum.sort(overall, :desc)
      assert Players.search(%{nationality: "Brazilian"}) == ps
    end

    test "Scenario: filter by club and position group" do
      ps = Players.search(%{club: "Santos"})
      assert ps != []
      assert Enum.all?(ps, &(&1.club in ["Santos", "Santos Laguna"]))

      # club names are normalised like team names
      assert Players.search(%{club: "Gremio"}) |> Enum.all?(&(&1.club == "Grêmio"))

      assert Players.search(%{club: "Atletico-MG"}) |> Enum.map(& &1.club) |> Enum.uniq() == [
               "Atlético Mineiro"
             ]

      fwd = Players.search(%{club: "Grêmio", position: "forwards"})
      assert fwd != []
      assert Enum.all?(fwd, &(&1.position in ~w(ST LS RS CF LF RF LW RW)))

      assert Players.search(%{club: "Grêmio", position: "GK"})
             |> Enum.all?(&(&1.position == "GK"))
    end

    test "Scenario: Brazilian players grouped by Brazilian club" do
      clubs = Players.by_club(%{nationality: "Brazil", brazilian_clubs_only: true})
      names = Enum.map(clubs, & &1.club)
      assert "Grêmio" in names and "Cruzeiro" in names
      refute "Paris Saint-Germain" in names
      assert Enum.all?(clubs, &(&1.players > 0 and &1.avg_overall > 40))
    end
  end

  describe "Feature: performance" do
    test "lookups and aggregates are fast once data is loaded" do
      {t1, _} = :timer.tc(fn -> Queries.matches(%{team: "Flamengo", opponent: "Corinthians"}) end)
      {t2, _} = :timer.tc(fn -> Queries.rankings(%{venue: "away"}, min_matches: 20) end)
      {t3, _} = :timer.tc(fn -> Players.search(%{nationality: "Brazil"}) end)
      assert t1 < 2_000_000
      assert t2 < 5_000_000
      assert t3 < 2_000_000
    end
  end
end
