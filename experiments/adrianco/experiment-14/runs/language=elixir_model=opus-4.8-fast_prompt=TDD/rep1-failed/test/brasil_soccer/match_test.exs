defmodule BrasilSoccer.MatchTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.Match

  describe "new/1" do
    test "normalises team names and computes comparison keys" do
      m =
        Match.new(%{
          competition: "Brasileirão",
          season: 2012,
          home_team: "Palmeiras-SP",
          away_team: "Grêmio-RS",
          home_goal: 2,
          away_goal: 1
        })

      assert m.home_team == "Palmeiras"
      assert m.away_team == "Grêmio"
      assert m.home_key == BrasilSoccer.Normalize.key("Palmeiras")
      assert m.away_key == BrasilSoccer.Normalize.key("Grêmio")
    end

    test "derives the winner from the scoreline" do
      assert Match.new(%{home_goal: 2, away_goal: 1}).winner == :home
      assert Match.new(%{home_goal: 0, away_goal: 3}).winner == :away
      assert Match.new(%{home_goal: 1, away_goal: 1}).winner == :draw
    end

    test "leaves winner nil when goals are missing" do
      assert Match.new(%{home_goal: nil, away_goal: 2}).winner == nil
    end
  end

  describe "involves?/2 and result_for/2" do
    setup do
      {:ok, match: Match.new(%{home_team: "Flamengo-RJ", away_team: "Santos-SP", home_goal: 3, away_goal: 0})}
    end

    test "involves?/2 matches either side by name", %{match: m} do
      assert Match.involves?(m, "flamengo")
      assert Match.involves?(m, "Santos")
      refute Match.involves?(m, "Palmeiras")
    end

    test "result_for/2 returns :win/:loss/:draw from a team's perspective", %{match: m} do
      assert Match.result_for(m, "Flamengo") == :win
      assert Match.result_for(m, "Santos") == :loss
    end

    test "result_for/2 returns nil for a team not in the match", %{match: m} do
      assert Match.result_for(m, "Palmeiras") == nil
    end
  end
end
