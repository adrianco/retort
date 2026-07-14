defmodule BrazilianSoccer.TeamNameTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.TeamName

  describe "clean/1" do
    test "strips a hyphenated state suffix" do
      assert TeamName.clean("Palmeiras-SP") == "Palmeiras"
      assert TeamName.clean("Flamengo-RJ") == "Flamengo"
    end

    test "strips a spaced state suffix" do
      assert TeamName.clean("América - MG") == "América"
    end

    test "strips a trailing country code in parentheses" do
      assert TeamName.clean("Nacional (URU)") == "Nacional"
    end

    test "strips a hyphenated country code" do
      assert TeamName.clean("Barcelona-EQU") == "Barcelona"
    end

    test "leaves a plain name untouched" do
      assert TeamName.clean("Santos") == "Santos"
    end

    test "collapses surrounding whitespace" do
      assert TeamName.clean("  Grêmio  ") == "Grêmio"
    end
  end

  describe "key/1 (identity, suffix preserved)" do
    test "is accent and case insensitive" do
      assert TeamName.key("São Paulo") == TeamName.key("Sao Paulo")
      assert TeamName.key("Grêmio") == TeamName.key("gremio")
    end

    test "keeps the state suffix so distinct clubs stay distinct" do
      assert TeamName.key("Atletico-MG") != TeamName.key("Atletico-PR")
      assert TeamName.key("Palmeiras-SP") == "palmeiras-sp"
    end
  end

  describe "base/1 (fuzzy, suffix stripped)" do
    test "ignores the state suffix" do
      assert TeamName.base("Palmeiras-SP") == TeamName.base("Palmeiras")
      assert TeamName.base("São Paulo-SP") == "sao paulo"
    end
  end

  describe "matches?/2" do
    test "matches across naming variations" do
      assert TeamName.matches?("Flamengo-RJ", "flamengo")
      assert TeamName.matches?("São Paulo", "Sao Paulo-SP")
    end

    test "does not match different teams" do
      refute TeamName.matches?("Flamengo", "Fluminense")
    end
  end
end
