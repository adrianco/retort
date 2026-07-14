defmodule BrSoccer.QueriesTest do
  @moduledoc "Query-logic tests against a small, deterministic fixture dataset."
  use ExUnit.Case, async: false

  alias BrSoccer.{Competitions, Fixtures, Matches, Players, Repo, Stats, Teams}

  setup do
    Repo.put_data(Fixtures.data())
    :ok
  end

  describe "Matches.search/1" do
    test "filters by team across home and away" do
      results = Matches.search(team: "Alpha")
      # Alpha appears in 7 of the 9 fixture matches.
      assert length(results) == 7
      assert Enum.all?(results, &(&1.home_key == "alpha" or &1.away_key == "alpha"))
    end

    test "filters by venue" do
      home = Matches.search(team: "Alpha", venue: :home, competition: :brasileirao, season: 2020)
      assert Enum.all?(home, &(&1.home == "Alpha"))
      assert length(home) == 2
    end

    test "filters by competition and season" do
      assert Matches.search(competition: :brasileirao, season: 2020) |> length() == 6
      assert Matches.search(competition: :libertadores) |> length() == 1
    end

    test "filters by date range" do
      results = Matches.search(from: ~D[2020-08-01], to: ~D[2020-08-15])
      assert length(results) == 3
    end

    test "sorts most-recent-first by default" do
      [first | _] = Matches.search(competition: :brasileirao, season: 2020)
      assert first.date == ~D[2020-09-05]
    end
  end

  describe "Matches.head_to_head/3" do
    test "counts wins, draws and goals from each club's perspective" do
      h = Matches.head_to_head("Alpha", "Beta", competition: :brasileirao, season: 2020)
      assert h.total == 2
      assert h.a_wins == 1
      assert h.b_wins == 0
      assert h.draws == 1
      assert h.a_goals == 3
      assert h.b_goals == 1
    end

    test "spans all competitions when unfiltered" do
      h = Matches.head_to_head("Alpha", "Beta")
      # 2020 league x2, 2019 league x1, libertadores x1
      assert h.total == 4
      assert h.a_wins == 3
    end
  end

  describe "Teams.record/2" do
    test "computes W/D/L, goals and win rate" do
      r = Teams.record("Alpha", competition: :brasileirao, season: 2020)
      assert r.matches == 4
      assert r.wins == 2
      assert r.draws == 2
      assert r.losses == 0
      assert r.goals_for == 6
      assert r.goals_against == 2
      assert r.points == 8
      assert r.win_rate == 50.0
    end
  end

  describe "Teams.biggest_wins/1" do
    test "limit bounds the result, not the match set that is scanned" do
      # The biggest margin in the fixtures is the 5-0 Libertadores tie, which is
      # NOT the most recent match. A limit of 1 must still surface it.
      [%{match: m, margin: margin}] = Teams.biggest_wins(limit: 1)
      assert margin == 5
      assert m.competition == :libertadores
    end
  end

  describe "Competitions.standings/2" do
    test "ranks the fixture league correctly" do
      table = Competitions.standings(:brasileirao, 2020)
      assert Enum.map(table, & &1.team) == ["Alpha", "Gamma", "Beta"]
      assert Enum.map(table, & &1.points) == [8, 5, 2]
      assert hd(table).position == 1
    end

    test "champion is the table leader" do
      assert Competitions.champion(:brasileirao, 2020).team == "Alpha"
    end
  end

  describe "Stats.summary/1" do
    test "aggregates goals and outcomes" do
      s = Stats.summary(competition: :brasileirao, season: 2020)
      assert s.matches == 6
      # goals: 2,2,4,0,4,1 = 13 over 6 matches
      assert s.total_goals == 13
      assert s.avg_goals == 2.17
      assert s.home_wins == 3
      assert s.draws == 3
    end
  end

  describe "Players" do
    test "search filters by nationality and sorts by overall" do
      brazilians = Players.search(nationality: "Brazil")
      assert Enum.map(brazilians, & &1.name) == ["Neymar Jr", "Alpha Star", "Beta Keeper", "Old Timer"]
    end

    test "search filters by club using normalised keys" do
      assert Players.search(club: "Alpha") |> length() == 3
    end

    test "search filters by position and min_overall" do
      assert [%{name: "Alpha Star"}] = Players.search(position: "ST")
      assert Players.search(min_overall: 85) |> Enum.map(& &1.name) == ["Neymar Jr", "Foreign Guy"]
    end

    test "groups Brazilians at Brazilian clubs with average ratings" do
      groups = Players.brazilians_at_brazilian_clubs()
      alpha = Enum.find(groups, &(&1.key == "alpha"))
      assert alpha.count == 2
      assert alpha.avg_overall == 75.0
      # Neymar's club (PSG) is not in the match data, so excluded.
      psg_key = BrSoccer.TeamName.key("Paris Saint-Germain")
      refute Enum.any?(groups, &(&1.key == psg_key))
    end
  end
end
