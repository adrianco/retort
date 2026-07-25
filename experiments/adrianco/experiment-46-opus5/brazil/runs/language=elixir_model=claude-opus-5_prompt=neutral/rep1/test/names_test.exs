defmodule BrazilianSoccer.NamesTest do
  @moduledoc """
  Feature: Team name normalisation

  The six datasets spell clubs differently; the graph needs one node per club.
  """

  use ExUnit.Case, async: true

  alias BrazilianSoccer.Names

  describe "Scenario: accents and casing" do
    test "Given accented Portuguese text When normalising Then accents are folded to ASCII" do
      assert Names.ascii("São Paulo") == "Sao Paulo"
      assert Names.ascii("Grêmio") == "Gremio"
      assert Names.ascii("Avaí") == "Avai"
      assert Names.ascii("Atlético Goianiense") == "Atletico Goianiense"
      assert Names.ascii("Fortaleza Esporte Clube") == "Fortaleza Esporte Clube"
    end

    test "Given accented and unaccented spellings When parsing Then the base is identical" do
      assert Names.parse("Grêmio").base == Names.parse("Gremio").base
      assert Names.parse("São Paulo").base == Names.parse("Sao Paulo").base
      assert Names.parse("Criciúma").base == Names.parse("Criciuma").base
    end
  end

  describe "Scenario: state and country suffixes" do
    test "Given a state suffix in any punctuation Then the base drops it and keeps the state" do
      for spelling <- ["Palmeiras-SP", "Palmeiras - SP", "Palmeiras SP", "palmeiras/sp"] do
        parsed = Names.parse(spelling)
        assert parsed.base == "palmeiras", "failed for #{spelling}"
        assert parsed.attr == "sp"
        assert parsed.attr_kind == :state
      end
    end

    test "Given a Libertadores country code Then it is kept as a country qualifier" do
      assert %{base: "nacional", attr: "uru", attr_kind: :country} = Names.parse("Nacional (URU)")
      assert %{base: "barcelona", attr: "equ"} = Names.parse("Barcelona-EQU")
    end

    test "Given no suffix Then there is no qualifier" do
      assert %{base: "palmeiras", attr: nil} = Names.parse("Palmeiras")
    end
  end

  describe "Scenario: club-type words and abbreviations" do
    test "Given club words When parsing Then only the identifying part survives" do
      assert Names.parse("Fortaleza Esporte Clube").base == "fortaleza"
      assert Names.parse("EC Bahia").base == "bahia"
      assert Names.parse("Vitoria EC").base == "vitoria"
      assert Names.parse("Clube Do Remo").base == "remo"
      assert Names.parse("Santa Cruz FC").base == "santa cruz"
    end

    test "Given initials with dots Then they collapse into one token" do
      assert Names.parse("A.b.c. - RN").base == "abc"
      assert Names.parse("A.s.a. - AL").base == "asa"
    end

    test "Given a parenthetical aside Then it is dropped" do
      parsed = Names.parse("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
      assert parsed.base == "boavista"
      assert parsed.attr == "rj"
    end

    test "Given a parenthetical state name Then it becomes the state code" do
      assert %{base: "america", attr: "mg"} = Names.parse("América FC (Minas Gerais)")
    end
  end

  describe "Scenario: known alternative club names" do
    test "Given the many names of one club Then they share a base and state" do
      for {spelling, base, attr} <- [
            {"Atlético Mineiro", "atletico", "mg"},
            {"Atlético - MG", "atletico", "mg"},
            {"Athletico Paranaense", "athletico", "pr"},
            {"Atletico-PR", "athletico", "pr"},
            {"Atletico Paranaense", "athletico", "pr"},
            {"Sport Club do Recife", "sport", "pe"},
            {"Sport Recife", "sport", "pe"},
            {"Sport-PE", "sport", "pe"},
            {"Nautico Capibaribe", "nautico", "pe"},
            {"Vasco", "vasco da gama", "rj"},
            {"Vasco da Gama-RJ", "vasco da gama", "rj"},
            {"Red Bull Bragantino-SP", "bragantino", "sp"},
            {"Portuguesa Desportos", "portuguesa", "sp"},
            {"Ceará Sporting Club", "ceara", "ce"}
          ] do
        parsed = Names.parse(spelling)
        assert {parsed.base, parsed.attr} == {base, attr}, "failed for #{spelling}"
      end
    end
  end

  describe "Scenario: resolving ambiguous club names" do
    test "Given one club per base Then the id has no qualifier" do
      keys = Names.resolve_keys(Enum.map(["Palmeiras-SP", "Palmeiras"], &Names.parse/1))

      assert keys[{"palmeiras", "sp"}] == "palmeiras"
      assert keys[{"palmeiras", nil}] == "palmeiras"
    end

    test "Given several clubs sharing a base Then the state stays in the id" do
      keys =
        ["Botafogo-RJ", "Botafogo SP", "Botafogo - PB", "Botafogo"]
        |> Enum.map(&Names.parse/1)
        |> Names.resolve_keys()

      assert keys[{"botafogo", "rj"}] == "botafogo-rj"
      assert keys[{"botafogo", "sp"}] == "botafogo-sp"
      assert keys[{"botafogo", "pb"}] == "botafogo-pb"

      # a bare "Botafogo" is the Rio club by default
      assert keys[{"botafogo", nil}] == "botafogo-rj"
    end

    test "Given no configured default Then the most common state wins" do
      keys =
        (List.duplicate("Ypiranga-RS", 5) ++ ["Ypiranga AP", "Ypiranga"])
        |> Enum.map(&Names.parse/1)
        |> Names.resolve_keys()

      assert keys[{"ypiranga", nil}] == "ypiranga-rs"
      assert keys[{"ypiranga", "ap"}] == "ypiranga-ap"
    end
  end

  describe "Scenario: display names" do
    test "Given a curated club Then the accented name is used" do
      assert Names.display_name("gremio", ["Gremio-RS", "Gremio"]) == "Grêmio"
      assert Names.display_name("sao paulo", ["Sao Paulo-SP"]) == "São Paulo"
    end

    test "Given an unknown club Then the accented spelling from the data is preferred" do
      assert Names.display_name("aguia negra", ["Aguia Negra-MS", "Águia Negra"]) ==
               "Águia Negra"
    end
  end

  describe "Scenario: similarity for fuzzy lookups" do
    test "Given identical, prefix and unrelated names Then similarity ranks them" do
      assert Names.similarity("flamengo", "flamengo") == 1.0
      assert Names.similarity("fla", "flamengo") > 0.9
      assert Names.similarity("flamengo", "palmeiras") < 0.6
      assert Names.similarity("", "flamengo") == 0.0
    end
  end

  describe "Scenario: junk input" do
    test "Given empty or nil input Then parsing returns nil rather than raising" do
      assert Names.parse(nil) == nil
      assert Names.parse("") == nil
      assert Names.parse("   ") == nil
    end
  end
end
