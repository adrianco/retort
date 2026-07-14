defmodule BrazilianSoccer.MatchTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Match

  describe "new/1" do
    test "cleans team names and stores matching keys" do
      m =
        Match.new(
          competition: "Brasileirão Série A",
          season: 2012,
          home_team: "Palmeiras-SP",
          away_team: "São Paulo-SP",
          home_goals: 2,
          away_goals: 1
        )

      assert m.home_team == "Palmeiras"
      assert m.away_team == "São Paulo"
      assert m.home_key == "palmeiras-sp"
      assert m.away_key == "sao paulo-sp"
      assert m.home_base == "palmeiras"
      assert m.away_base == "sao paulo"
    end

    test "parses string goals into integers" do
      m = Match.new(home_team: "A", away_team: "B", home_goals: "3", away_goals: "0")
      assert m.home_goals == 3
      assert m.away_goals == 0
    end

    test "parses an ISO datetime into a Date" do
      m = Match.new(home_team: "A", away_team: "B", date: "2012-05-19 18:30:00")
      assert m.date == ~D[2012-05-19]
    end

    test "parses a Brazilian DD/MM/YYYY date" do
      m = Match.new(home_team: "A", away_team: "B", date: "29/03/2003")
      assert m.date == ~D[2003-03-29]
    end

    test "parses a plain ISO date" do
      m = Match.new(home_team: "A", away_team: "B", date: "2023-09-24")
      assert m.date == ~D[2023-09-24]
    end

    test "tolerates missing/blank goals and dates" do
      m = Match.new(home_team: "A", away_team: "B", home_goals: "", date: "")
      assert m.home_goals == nil
      assert m.date == nil
    end

    test "infers season from the date when not given" do
      m = Match.new(home_team: "A", away_team: "B", date: "2019-11-10")
      assert m.season == 2019
    end
  end

  describe "result helpers" do
    test "winner/1 returns :home, :away or :draw" do
      assert Match.winner(Match.new(home_team: "A", away_team: "B", home_goals: 2, away_goals: 1)) == :home
      assert Match.winner(Match.new(home_team: "A", away_team: "B", home_goals: 0, away_goals: 1)) == :away
      assert Match.winner(Match.new(home_team: "A", away_team: "B", home_goals: 1, away_goals: 1)) == :draw
    end

    test "winner/1 is nil when goals are unknown" do
      assert Match.winner(Match.new(home_team: "A", away_team: "B")) == nil
    end

    test "involves?/2 matches either side by normalized name" do
      m = Match.new(home_team: "Flamengo-RJ", away_team: "Fluminense-RJ")
      assert Match.involves?(m, "flamengo")
      assert Match.involves?(m, "Fluminense")
      refute Match.involves?(m, "Santos")
    end

    test "total_goals/1 sums the score" do
      assert Match.total_goals(Match.new(home_team: "A", away_team: "B", home_goals: 2, away_goals: 3)) == 5
      assert Match.total_goals(Match.new(home_team: "A", away_team: "B")) == nil
    end
  end
end
