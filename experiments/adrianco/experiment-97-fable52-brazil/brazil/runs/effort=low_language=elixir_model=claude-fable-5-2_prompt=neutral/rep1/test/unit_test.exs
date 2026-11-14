defmodule BrazilianSoccer.UnitTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.{CSV, TeamNames, Text}

  describe "CSV parser" do
    test "handles quotes, escaped quotes, embedded commas, CRLF and BOM" do
      csv =
        "﻿name,joined,note\r\n\"Silva, T.\",\"Jul 1, 2004\",\"said \"\"oi\"\"\"\r\nGrêmio,,x\n"

      assert CSV.parse_maps(csv) == [
               %{"name" => "Silva, T.", "joined" => "Jul 1, 2004", "note" => "said \"oi\""},
               %{"name" => "Grêmio", "joined" => "", "note" => "x"}
             ]
    end

    test "empty input and trailing blank lines" do
      assert CSV.parse("") == []
      assert CSV.parse("a,b\n\n") == [["a", "b"]]
    end
  end

  describe "date formats" do
    test "ISO, ISO with time and Brazilian formats" do
      assert Text.parse_datetime("2023-09-24") == {~D[2023-09-24], nil}
      assert Text.parse_datetime("2012-05-19 18:30:00") == {~D[2012-05-19], "18:30"}
      assert Text.parse_datetime("29/03/2003") == {~D[2003-03-29], nil}
      assert Text.parse_datetime("NA") == nil
      assert Text.parse_datetime("2023-02-31") == nil
    end

    test "numbers" do
      assert Text.to_int("1.0") == 1
      assert Text.to_int("3") == 3
      assert Text.to_int("NA") == nil
      assert Text.to_int("-") == nil
    end
  end

  describe "team name normalisation" do
    test "state suffixes, accents and spelling variants reduce to the same club" do
      for {names, expected} <- [
            {["Palmeiras-SP", "Palmeiras", "Palmeiras - SP", "Sociedade Esportiva Palmeiras"],
             "palmeiras"},
            {["Grêmio", "Gremio-RS", "Gremio"], "gremio"},
            {["São Paulo", "Sao Paulo-SP", "São Paulo FC", "Sao Paulo"], "sao paulo"},
            {["Vasco da Gama-RJ", "Vasco", "Vasco Da Gama RJ"], "vasco"},
            {["EC Bahia", "Bahia - BA", "Bahia"], "bahia"},
            {["Sport Club Corinthians Paulista", "Corinthians - SP"], "corinthians"},
            {["C. R. B. - AL", "C.r.b. - AL", "Crb - AL", "CRB"], "crb"},
            {["Avaí", "Avai-SC"], "avai"}
          ],
          name <- names do
        assert {^expected, _state, _} = TeamNames.parse(name),
               "#{name} should normalise to #{expected}"
      end
    end

    test "clubs sharing a name are told apart by state" do
      assert {"atletico", "MG", _} = TeamNames.parse("Atlético-MG")
      assert {"atletico", "MG", _} = TeamNames.parse("Atletico Mineiro")
      assert {"atletico", "PR", _} = TeamNames.parse("Athletico-PR")
      assert {"atletico", "PR", _} = TeamNames.parse("Atlético Paranaense")
      assert {"atletico", "GO", _} = TeamNames.parse("Atletico Goianiense")
      assert {"flamengo", "PI", _} = TeamNames.parse("Flamengo - PI")
      assert {"nacional", "URU", _} = TeamNames.parse("Nacional (URU)")
      assert {"barcelona", "EQU", _} = TeamNames.parse("Barcelona-EQU")
    end

    test "names that merely look like suffixes are left alone" do
      assert {"colo-colo", nil, _} = TeamNames.parse("Colo-Colo")

      assert {"boavista", "RJ", _} =
               TeamNames.parse("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ")
    end
  end
end
