defmodule BrasilSoccer.NormalizeTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.Normalize

  describe "team_name/1 (display name)" do
    test "strips a hyphenated state suffix" do
      assert Normalize.team_name("Palmeiras-SP") == "Palmeiras"
      assert Normalize.team_name("Flamengo-RJ") == "Flamengo"
    end

    test "strips a spaced-hyphen state suffix" do
      assert Normalize.team_name("América - MG") == "América"
    end

    test "strips a parenthesised country code" do
      assert Normalize.team_name("Nacional (URU)") == "Nacional"
      assert Normalize.team_name("Barcelona-EQU") == "Barcelona"
    end

    test "keeps a trailing hyphen group that is not a state/country code" do
      assert Normalize.team_name("Vasco da Gama") == "Vasco da Gama"
    end

    test "trims surrounding whitespace" do
      assert Normalize.team_name("  Santos  ") == "Santos"
    end
  end

  describe "key/1 (match key)" do
    test "is case-insensitive and accent-insensitive" do
      assert Normalize.key("Grêmio") == Normalize.key("gremio")
      assert Normalize.key("São Paulo") == Normalize.key("sao paulo")
    end

    test "ignores the state/country suffix so variants collapse" do
      assert Normalize.key("Palmeiras-SP") == Normalize.key("Palmeiras")
      assert Normalize.key("Nacional (URU)") == Normalize.key("Nacional")
    end

    test "collapses internal whitespace" do
      assert Normalize.key("Atletico  MG") == Normalize.key("Atletico MG")
    end
  end

  describe "matches?/2" do
    test "true when one name is contained in the other after normalisation" do
      assert Normalize.matches?("Flamengo-RJ", "flamengo")
      assert Normalize.matches?("São Paulo FC", "sao paulo")
      refute Normalize.matches?("Santos", "Palmeiras")
    end
  end
end
