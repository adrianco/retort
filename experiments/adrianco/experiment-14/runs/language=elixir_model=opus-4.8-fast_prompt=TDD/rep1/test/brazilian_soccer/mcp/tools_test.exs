defmodule BrazilianSoccer.MCP.ToolsTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.MCP.Tools

  setup do
    {:ok, dataset: BrazilianSoccer.Fixtures.dataset()}
  end

  describe "list/0" do
    test "exposes tool specs with names and input schemas" do
      tools = Tools.list()
      names = Enum.map(tools, & &1.name)

      assert "search_matches" in names
      assert "team_record" in names
      assert "search_players" in names
      assert "standings" in names

      assert Enum.all?(tools, fn t ->
               is_binary(t.name) and is_binary(t.description) and
                 t.input_schema["type"] == "object"
             end)
    end
  end

  describe "call/3" do
    test "search_matches summarizes results", %{dataset: ds} do
      {:ok, text} = Tools.call("search_matches", %{"team" => "Flamengo", "opponent" => "Fluminense"}, ds)
      assert text =~ "Flamengo"
      assert text =~ "Fluminense"
      # Head-to-head summary when two teams are given.
      assert text =~ "Head-to-head"
    end

    test "team_record reports a win/loss/draw line", %{dataset: ds} do
      {:ok, text} = Tools.call("team_record", %{"team" => "Flamengo", "season" => 2023}, ds)
      assert text =~ "Wins: 2"
      assert text =~ "Goals For: 5"
    end

    test "search_players lists ranked players", %{dataset: ds} do
      {:ok, text} = Tools.call("search_players", %{"brazilian" => true, "limit" => 2}, ds)
      assert text =~ "Neymar Jr"
      assert text =~ "92"
    end

    test "standings renders a table with the champion first", %{dataset: ds} do
      {:ok, text} = Tools.call("standings", %{"competition" => "Brasileirão Série A", "season" => 2023}, ds)
      assert text =~ "Palmeiras"
      assert text =~ "1."
    end

    test "match_stats returns aggregate numbers", %{dataset: ds} do
      {:ok, text} = Tools.call("match_stats", %{}, ds)
      assert text =~ "Average goals per match"
    end

    test "unknown tool returns an error", %{dataset: ds} do
      assert {:error, msg} = Tools.call("nope", %{}, ds)
      assert msg =~ "Unknown tool"
    end

    test "missing required argument returns an error", %{dataset: ds} do
      assert {:error, _} = Tools.call("team_record", %{}, ds)
    end
  end
end
