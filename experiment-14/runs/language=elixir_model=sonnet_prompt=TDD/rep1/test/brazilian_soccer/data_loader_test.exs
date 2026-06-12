defmodule BrazilianSoccer.DataLoaderTest do
  use ExUnit.Case, async: false

  alias BrazilianSoccer.DataLoader

  describe "parse_brasileirao/1" do
    test "parses a CSV row into a match struct" do
      row = ["2012-05-19 18:30:00", "Palmeiras-SP", "SP", "Portuguesa-SP", "SP", "1", "1", "2012", "1"]
      match = DataLoader.parse_brasileirao_row(row)
      assert match.home_team == "Palmeiras"
      assert match.away_team == "Portuguesa"
      assert match.home_goal == 1
      assert match.away_goal == 1
      assert match.season == 2012
      assert match.round == 1
      assert match.competition == "Brasileirão"
    end

    test "strips state suffix from team names" do
      row = ["2023-09-03 18:30:00", "Flamengo-RJ", "RJ", "Fluminense-RJ", "RJ", "2", "1", "2023", "22"]
      match = DataLoader.parse_brasileirao_row(row)
      assert match.home_team == "Flamengo"
      assert match.away_team == "Fluminense"
    end
  end

  describe "parse_cup_row/1" do
    test "parses a Copa do Brasil CSV row" do
      row = ["1", "2012-03-07 16:00:00", "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "América - MG", "0", "0", "2012"]
      match = DataLoader.parse_cup_row(row)
      assert match.home_goal == 0
      assert match.away_goal == 0
      assert match.season == 2012
      assert match.competition == "Copa do Brasil"
    end
  end

  describe "parse_libertadores_row/1" do
    test "parses a Libertadores CSV row" do
      row = ["2013-02-12 20:15:00", "Nacional (URU)", "Barcelona-EQU", "2", "2", "2013", "group stage"]
      match = DataLoader.parse_libertadores_row(row)
      assert match.home_goal == 2
      assert match.away_goal == 2
      assert match.season == 2013
      assert match.competition == "Copa Libertadores"
      assert match.stage == "group stage"
    end
  end

  describe "parse_historico_row/1" do
    test "parses a historical Brasileirão row with Brazilian date format" do
      row = ["2003.01.0001", "29/03/2003", "2003", "1", "Guarani", "Vasco", "4", "2", "SP", "RJ", "Mandante", "Brinco de Ouro", ""]
      match = DataLoader.parse_historico_row(row)
      assert match.home_team == "Guarani"
      assert match.away_team == "Vasco"
      assert match.home_goal == 4
      assert match.away_goal == 2
      assert match.season == 2003
      assert match.competition == "Brasileirão"
    end
  end

  describe "parse_player_row/1" do
    test "parses a FIFA player row" do
      row = ["0", "158023", "L. Messi", "31", "", "Argentina", "", "94", "94",
             "FC Barcelona", "", "€110.5M", "€565K", "2202", "Left", "5", "4", "4",
             "Medium/ Medium", "Messi", "Yes", "RF", "10", "Jul 1, 2004", "", "2021",
             "5'7", "159lbs"] ++ List.duplicate("", 60)
      player = DataLoader.parse_player_row(row)
      assert player.name == "L. Messi"
      assert player.age == 31
      assert player.nationality == "Argentina"
      assert player.overall == 94
      assert player.club == "FC Barcelona"
      assert player.position == "RF"
    end
  end

  describe "normalize_team_name/1" do
    test "removes state suffix" do
      assert DataLoader.normalize_team_name("Palmeiras-SP") == "Palmeiras"
      assert DataLoader.normalize_team_name("Flamengo-RJ") == "Flamengo"
    end

    test "removes ' - STATE' suffix" do
      assert DataLoader.normalize_team_name("América - MG") == "América"
      assert DataLoader.normalize_team_name("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ") ==
             "Boavista Sport Club (antigo Esporte Clube Barreira)"
    end

    test "leaves names without suffix unchanged" do
      assert DataLoader.normalize_team_name("Palmeiras") == "Palmeiras"
      assert DataLoader.normalize_team_name("Flamengo") == "Flamengo"
    end
  end

  describe "parse_br_football_row/1" do
    test "parses BR-Football-Dataset row" do
      row = ["Copa do Brasil", "Sao Paulo", "1.0", "1.0", "Flamengo", "2.0", "4.0",
             "75.0", "104.0", "8.0", "13.0", "20:00:00", "2023-09-24",
             "0.0", "0.0", "DRAW", "DRAW", "6.0"]
      match = DataLoader.parse_br_football_row(row)
      assert match.home_team == "Sao Paulo"
      assert match.away_team == "Flamengo"
      assert match.home_goal == 1
      assert match.away_goal == 1
      assert match.competition == "Copa do Brasil"
    end
  end
end
