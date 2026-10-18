defmodule SoccerMcp.TeamTest do
  # Feature: Team name normalization
  #   The same club is written with a state suffix, a country, accents or
  #   its full legal name. Queries must match all of these.
  use ExUnit.Case, async: true

  alias SoccerMcp.Team

  describe "Feature: team name variations" do
    test "Scenario: state suffixes are removed" do
      # Given a team name with a state suffix
      # When I normalize it
      # Then the suffix is gone and the keys agree
      assert Team.key("Palmeiras-SP") == "palmeiras"
      assert Team.key("Palmeiras") == "palmeiras"
      assert Team.key("Flamengo - RJ") == Team.key("Flamengo-RJ")
    end

    test "Scenario: accents and case are ignored" do
      # Given accented and upper-case spellings
      # When I normalize them
      # Then they share one key
      assert Team.key("GRÊMIO") == Team.key("Gremio")
      assert Team.key("Atlético Paranaense - PR") == Team.key("Athletico-PR")
    end

    test "Scenario: full legal names map to the short name" do
      # Given a full legal name
      # When I normalize it
      # Then it reduces to the name people use
      assert Team.key("Sport Club Corinthians Paulista") == "corinthians"
    end

    test "Scenario: parenthesised former names are dropped" do
      # Given a name with a former name in brackets
      # When I normalize it
      # Then only the current name remains
      assert Team.key("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ") ==
               "boavista sport club"
    end

    test "Scenario: trailing EC/FC is treated as the same club" do
      # Given "4 de Julho EC" from one file and "4 de Julho" from another
      # When I normalize both
      # Then they match
      assert Team.key("4 de Julho EC - PI") == Team.key("4 de Julho")
    end

    test "Scenario: a query matches whole words only" do
      # Given a stored key
      # When I query with a whole-word part of it
      # Then it matches, and a partial word does not
      assert Team.matches?("sao paulo", "sao paulo")
      assert Team.matches?("sport recife", "recife")
      assert Team.matches?("sao paulo", "paulo")
      refute Team.matches?("sao paulo", "pau")
      refute Team.matches?("flamengo", "")
    end

    test "Scenario: the state code is read from the name" do
      # Given names with and without a state suffix
      # When I read their state
      # Then the suffix gives the state, and names without one give nil
      assert Team.state("Atlético - MG") == "mg"
      assert Team.state("Atletico-GO") == "go"
      assert Team.state("Botafogo RJ") == "rj"
      assert Team.state("Flamengo") == nil
      assert Team.state("Barcelona-EQU") == nil
    end

    test "Scenario: a missing state is compatible with any state" do
      # Given one known state and one unknown
      # Then they do not contradict each other, but two different states do
      assert Team.compatible_states?(nil, "mg")
      assert Team.compatible_states?("mg", "mg")
      refute Team.compatible_states?("mg", "go")
    end

    test "Scenario: display names keep accents and drop suffixes" do
      # Given a raw name
      # When I ask for its display form
      # Then accents remain and the state suffix is removed
      assert Team.display("São Paulo - SP") == "São Paulo"
    end
  end
end
