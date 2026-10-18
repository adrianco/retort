defmodule BrazilianSoccer.NormalizeTest do
  use ExUnit.Case, async: true

  doctest BrazilianSoccer.Normalize

  alias BrazilianSoccer.Normalize

  describe "Scenario: team name variations resolve to one key" do
    test "Given state suffixes, then they are ignored" do
      assert Normalize.team_key("Palmeiras-SP") == "palmeiras"
      assert Normalize.team_key("Palmeiras") == "palmeiras"
      assert Normalize.team_key("Fluminense - RJ") == "fluminense"
    end

    test "Given accents and cedillas, then they fold away" do
      assert Normalize.team_key("Grêmio") == "gremio"
      assert Normalize.team_key("Atlético-MG") == "atletico"
      assert Normalize.team_key("São Paulo") == Normalize.team_key("Sao Paulo-SP")
    end

    test "Given a country code or a parenthetical note, then it is removed" do
      assert Normalize.team_key("Nacional (URU)") == "nacional"
      assert Normalize.team_key("Barcelona-EQU") == "barcelona"

      assert Normalize.display_name("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ") ==
               "Boavista Sport Club"
    end

    test "Given a long official name, then the alias maps it to the short key" do
      assert Normalize.team_key("Sport Club Corinthians Paulista") == "corinthians"
      assert Normalize.team_key("Clube de Regatas do Flamengo") == "flamengo"
    end

    test "Given state codes without a hyphen, then they are removed" do
      assert Normalize.team_key("Vasco Da Gama RJ") == "vasco"
      assert Normalize.team_key("Operário FC MS") == "operario"
      assert Normalize.team_key("Botafogo RJ") == Normalize.team_key("Botafogo")
    end

    test "Given EC/FC club words as prefix or suffix, then they are removed" do
      assert Normalize.team_key("EC Bahia") == "bahia"
      assert Normalize.team_key("Fortaleza FC") == "fortaleza"
      assert Normalize.team_key("CR Flamengo") == "flamengo"
    end

    test "Given known spelling variants of one club, then they share a key" do
      assert Normalize.team_key("Atletico Paranaense") == Normalize.team_key("Athletico-PR")
      assert Normalize.team_key("Atletico Mineiro") == Normalize.team_key("Atlético-MG")
      assert Normalize.team_key("River Plate") == Normalize.team_key("River")
      assert Normalize.team_key("C.R.B.") == Normalize.team_key("CRB")
    end

    test "Given a name that is not a team suffix, then it is kept" do
      assert Normalize.display_name("Gremio Foot-Ball") == "Gremio Foot-Ball"
    end
  end

  describe "Scenario: numeric cells" do
    test "Given integers, floats and blanks, then they convert to integers or nil" do
      assert Normalize.integer("2") == 2
      assert Normalize.integer("2.0") == 2
      assert Normalize.integer(" 7 ") == 7
      assert Normalize.integer("") == nil
      assert Normalize.integer("€565K") == nil
    end
  end
end
