defmodule BrazilianSoccerMcp.TeamNamesTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccerMcp.TeamNames

  describe "Given team name variations across datasets, when normalized" do
    test "then state-suffixed and plain spellings produce the same key" do
      assert TeamNames.normalize("Palmeiras-SP").key == TeamNames.normalize("Palmeiras").key
      assert TeamNames.normalize("Flamengo-RJ").key == TeamNames.normalize("Flamengo").key
      assert TeamNames.normalize("Sao Paulo-SP").key == TeamNames.normalize("São Paulo").key
    end

    test "then ' - UF' and ' UF' suffix styles also match" do
      assert TeamNames.normalize("América - MG").key == TeamNames.normalize("America MG").key
      assert TeamNames.normalize("Bahia - BA").key == TeamNames.normalize("Bahia").key
    end

    test "then accents and punctuation do not matter" do
      assert TeamNames.normalize("Grêmio").key == TeamNames.normalize("Gremio-RS").key
      assert TeamNames.normalize("A.s.a. - AL").key == TeamNames.normalize("ASA AL").key
      assert TeamNames.normalize("Avaí - SC").key == TeamNames.normalize("Avai-SC").key
    end

    test "then full official names map to the common name" do
      assert TeamNames.normalize("Sport Club Corinthians Paulista").key ==
               TeamNames.normalize("Corinthians-SP").key

      assert TeamNames.normalize("Vasco da Gama-RJ").key == TeamNames.normalize("Vasco").key

      assert TeamNames.normalize("Sport Club do Recife").key ==
               TeamNames.normalize("Sport-PE").key
    end

    test "then renamed/aliased clubs unify" do
      # Atlético-PR renamed to Athletico Paranaense
      assert TeamNames.normalize("Atlético - PR").key ==
               TeamNames.normalize("Athletico Paranaense").key

      assert TeamNames.normalize("Atletico Mineiro").key == TeamNames.normalize("Atlético-MG").key

      assert TeamNames.normalize("Red Bull Bragantino-SP").key ==
               TeamNames.normalize("Bragantino").key
    end

    test "then club-type words like EC/FC are ignored" do
      assert TeamNames.normalize("Fortaleza FC").key == TeamNames.normalize("Fortaleza-CE").key
      assert TeamNames.normalize("EC Juventude").key == TeamNames.normalize("Juventude-RS").key
      assert TeamNames.normalize("EC Bahia").key == TeamNames.normalize("Bahia-BA").key
    end

    test "then same-named clubs from different states stay distinct" do
      assert TeamNames.normalize("América - MG").key != TeamNames.normalize("América - RN").key
      assert TeamNames.normalize("Botafogo - PB").key != TeamNames.normalize("Botafogo-RJ").key
      assert TeamNames.normalize("Atlético-MG").key != TeamNames.normalize("Atlético-GO").key
    end

    test "then parenthetical notes are stripped" do
      assert TeamNames.normalize("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ").state ==
               "RJ"
    end

    test "then international clubs keep their country code" do
      assert TeamNames.normalize("Nacional (URU)").key == "nacional-uru"
      assert TeamNames.normalize("Barcelona-EQU").key != TeamNames.normalize("Barcelona").key
    end

    test "then known data errors are corrected" do
      # 'BH' used for Bahia in the historical file
      assert TeamNames.normalize("Bahia", "BH").key == TeamNames.normalize("Bahia", "BA").key
    end
  end
end
