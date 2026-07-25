defmodule BrazilianSoccer.PerformanceTest do
  @moduledoc """
  Feature: Query performance

  Scenario: The specification's budget
    Given the graph is loaded
    When a simple lookup runs
    Then it answers in well under 2 seconds
    And an aggregate query answers in well under 5 seconds
  """

  use BrazilianSoccer.GraphCase, async: false

  alias BrazilianSoccer.MCP.Tools

  @simple_budget_ms 2_000
  @aggregate_budget_ms 5_000

  defp measure(tool, args) do
    {microseconds, result} = :timer.tc(fn -> Tools.call(tool, args) end)
    assert {:ok, _} = result
    div(microseconds, 1000)
  end

  describe "Scenario: simple lookups" do
    test "Given a lookup tool Then it answers in under 2 seconds" do
      lookups = [
        {"search_matches", %{"team" => "Flamengo", "opponent" => "Fluminense", "limit" => 20}},
        {"last_meeting", %{"team_a" => "Flamengo", "team_b" => "Corinthians"}},
        {"team_profile", %{"team" => "Palmeiras"}},
        {"player_profile", %{"name" => "Neymar"}},
        {"resolve_team_name", %{"name" => "Atlético"}},
        {"league_standings", %{"season" => 2019}}
      ]

      for {tool, args} <- lookups do
        elapsed = measure(tool, args)
        assert elapsed < @simple_budget_ms, "#{tool} took #{elapsed}ms"
      end
    end
  end

  describe "Scenario: aggregate queries" do
    test "Given an aggregate tool Then it answers in under 5 seconds" do
      aggregates = [
        {"match_statistics", %{}},
        {"team_rankings", %{"metric" => "home", "competition" => "Brasileirão"}},
        {"biggest_wins", %{"limit" => 20}},
        {"players_by_nationality", %{"nationality" => "Brazil"}},
        {"compare_seasons", %{"seasons" => [2015, 2016, 2017, 2018, 2019]}},
        {"home_advantage", %{"competition" => "Brasileirão"}},
        {"team_stats", %{"team" => "Flamengo"}}
      ]

      for {tool, args} <- aggregates do
        elapsed = measure(tool, args)
        assert elapsed < @aggregate_budget_ms, "#{tool} took #{elapsed}ms"
      end
    end
  end

  describe "Scenario: repeated calls" do
    test "Given 50 consecutive tool calls Then none of them time out" do
      {microseconds, :ok} =
        :timer.tc(fn ->
          Enum.each(1..50, fn index ->
            season = 2003 + rem(index, 20)
            assert {:ok, _} = Tools.call("league_standings", %{"season" => season})
          end)
        end)

      assert div(microseconds, 1000) < @aggregate_budget_ms * 5
    end
  end
end
