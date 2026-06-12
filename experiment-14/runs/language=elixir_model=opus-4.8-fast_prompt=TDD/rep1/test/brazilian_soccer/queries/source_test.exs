defmodule BrazilianSoccer.Queries.SourceTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Match
  alias BrazilianSoccer.Queries.Source

  defp m(source, home, away) do
    Match.new(competition: "Brasileirão Série A", season: 2019, source: source, home_team: home, away_team: away, home_goals: 1, away_goals: 0)
  end

  test "keeps only the dominant source within each competition/season" do
    matches = [
      m("big.csv", "A", "B"),
      m("big.csv", "C", "D"),
      m("big.csv", "E", "F"),
      m("small.csv", "A", "B")
    ]

    result = Source.primary_per_season(matches)
    assert length(result) == 3
    assert Enum.all?(result, &(&1.source == "big.csv"))
  end

  test "keeps sources for different seasons independently" do
    a = m("a.csv", "A", "B")
    b = %{m("b.csv", "C", "D") | season: 2020}
    assert length(Source.primary_per_season([a, b])) == 2
  end
end
