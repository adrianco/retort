defmodule BrasilSoccer.MCP.ToolsTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.MCP.Tools
  alias BrasilSoccer.Fixtures

  setup do
    {:ok, data: %{matches: Fixtures.matches(), players: Fixtures.players()}}
  end

  describe "specs/0" do
    test "every tool has a name, description, and object input schema" do
      specs = Tools.specs()
      assert length(specs) >= 8

      for spec <- specs do
        assert is_binary(spec.name)
        assert is_binary(spec.description)
        assert spec.inputSchema["type"] == "object"
        assert is_map(spec.inputSchema["properties"])
      end
    end

    test "tool names are unique" do
      names = Tools.specs() |> Enum.map(& &1.name)
      assert names == Enum.uniq(names)
    end
  end

  describe "call/3 find_matches" do
    test "returns matches for a single team", %{data: data} do
      {:ok, text} = Tools.call("find_matches", %{"team" => "Flamengo"}, data)
      assert text =~ "Flamengo"
      assert text =~ "found"
    end

    test "includes head-to-head when two teams are given", %{data: data} do
      {:ok, text} = Tools.call("find_matches", %{"team" => "Flamengo", "opponent" => "Fluminense"}, data)
      assert text =~ "head-to-head"
    end

    test "requires at least one filter", %{data: data} do
      assert {:error, msg} = Tools.call("find_matches", %{}, data)
      assert msg =~ "team" or msg =~ "filter"
    end
  end

  describe "call/3 team_record" do
    test "summarises a team record", %{data: data} do
      {:ok, text} = Tools.call("team_record", %{"team" => "Flamengo"}, data)
      assert text =~ "Win rate"
    end

    test "errors without a team", %{data: data} do
      assert {:error, _} = Tools.call("team_record", %{}, data)
    end
  end

  describe "call/3 search_players" do
    test "filters by nationality", %{data: data} do
      {:ok, text} = Tools.call("search_players", %{"nationality" => "Brazil"}, data)
      assert text =~ "Neymar"
    end
  end

  describe "call/3 standings" do
    setup do
      {:ok, data: %{matches: Fixtures.mini_season(), players: []}}
    end

    test "renders the table", %{data: data} do
      {:ok, text} = Tools.call("standings", %{"competition" => "Brasileirão", "season" => 2019}, data)
      assert text =~ "1. Flamengo"
    end
  end

  describe "call/3 unknown tool" do
    test "returns an error", %{data: data} do
      assert {:error, msg} = Tools.call("nope", %{}, data)
      assert msg =~ "Unknown tool"
    end
  end
end
