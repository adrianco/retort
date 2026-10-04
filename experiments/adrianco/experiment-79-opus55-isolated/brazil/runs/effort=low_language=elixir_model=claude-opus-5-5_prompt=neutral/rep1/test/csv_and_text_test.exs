defmodule BrazilianSoccer.CSVAndTextTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.{CSV, Teams, Text}

  describe "Feature: CSV parsing" do
    test "handles quotes, embedded commas, escaped quotes, CRLF and a BOM" do
      csv = "﻿a,b,c\r\n1,\"x, y\",\"say \"\"hi\"\"\"\r\n2,,\"multi\nline\"\n"

      assert CSV.parse(csv) == [
               ["a", "b", "c"],
               ["1", "x, y", "say \"hi\""],
               ["2", "", "multi\nline"]
             ]
    end

    test "parses rows into maps keyed by header, without a trailing newline" do
      assert CSV.parse_maps("name,goals\nFlamengo,2") == [%{"name" => "Flamengo", "goals" => "2"}]
      assert CSV.parse_maps("") == []
    end
  end

  describe "Feature: date formats" do
    test "ISO, ISO with time and Brazilian formats are all understood" do
      assert Text.parse_date("2023-09-24") == ~D[2023-09-24]
      assert Text.parse_date("2012-05-19 18:30:00") == ~D[2012-05-19]
      assert Text.parse_date("29/03/2003") == ~D[2003-03-29]
      assert Text.parse_date("NA") == nil
      assert Text.parse_date("31/02/2003") == nil
    end

    test "numbers tolerate floats and missing markers" do
      assert Text.parse_int("2.0") == 2
      assert Text.parse_int("3") == 3
      assert Text.parse_int("NA") == nil
      assert Text.parse_int("-") == nil
    end
  end

  describe "Feature: team name normalisation" do
    test "state suffixes, accents and full names resolve to the same club" do
      for name <- [
            "Palmeiras-SP",
            "Palmeiras",
            "Palmeiras - SP",
            "palmeiras",
            "Sociedade Esportiva Palmeiras"
          ] do
        assert %{key: "palmeiras", state: "SP", name: "Palmeiras"} = Teams.resolve(name)
      end

      for name <- ["São Paulo", "Sao Paulo-SP", "São Paulo - SP", "Sao Paulo", "São Paulo FC"] do
        assert Teams.resolve(name).key == "sao paulo"
      end

      for name <- ["Grêmio", "Gremio-RS", "Gremio RS", "Grêmio - RS"] do
        assert %{key: "gremio", name: "Grêmio"} = Teams.resolve(name)
      end

      assert Teams.resolve("Sport Club Corinthians Paulista").key == "corinthians"
      assert Teams.resolve("Vasco da Gama - RJ").key == Teams.resolve("Vasco").key
    end

    test "clubs sharing a base name are told apart by state" do
      assert Teams.resolve("Atlético - MG").key == "atletico mineiro"
      assert Teams.resolve("Atletico-MG").key == "atletico mineiro"
      assert Teams.resolve("Atletico Mineiro").key == "atletico mineiro"
      assert Teams.resolve("Atletico-PR").key == "athletico paranaense"
      assert Teams.resolve("Athletico Paranaense - PR").key == "athletico paranaense"
      assert Teams.resolve("Atlético - GO").key == "atletico goianiense"

      rj = Teams.resolve("Botafogo")
      sp = Teams.resolve("Botafogo SP")
      assert rj.state == "RJ" and sp.state == "SP"
      refute Teams.same?(rj, sp.key, sp.state)
      assert Teams.resolve("Flamengo - PI").name == "Flamengo-PI"
    end

    test "foreign clubs keep a country code" do
      assert %{key: "nacional", state: "URU"} = Teams.resolve("Nacional (URU)")
      assert %{key: "nacional", state: "URU"} = Teams.resolve("Nacional-URU")
      assert %{key: "colo colo", state: nil} = Teams.resolve("Colo-Colo")
    end

    test "traditional rivalries are recognised in either order" do
      assert Teams.derby_name("flamengo", "fluminense") == "Fla-Flu"
      assert Teams.derby_name("internacional", "gremio") == "Gre-Nal"
      assert Teams.derby_name("flamengo", "santos") == nil
    end
  end
end
