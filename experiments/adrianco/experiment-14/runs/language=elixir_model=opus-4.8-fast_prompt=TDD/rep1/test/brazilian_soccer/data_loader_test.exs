defmodule BrazilianSoccer.DataLoaderTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.DataLoader

  describe "from_brasileirao/1" do
    test "maps rows, strips state suffixes and labels the competition" do
      rows = [
        %{
          "datetime" => "2012-05-19 18:30:00",
          "home_team" => "Palmeiras-SP",
          "away_team" => "Portuguesa-SP",
          "home_goal" => "1",
          "away_goal" => "1",
          "season" => "2012",
          "round" => "1"
        }
      ]

      assert [m] = DataLoader.from_brasileirao(rows)
      assert m.competition == "Brasileirão Série A"
      assert m.home_team == "Palmeiras"
      assert m.date == ~D[2012-05-19]
      assert m.season == 2012
      assert m.round == "1"
    end
  end

  describe "from_cup/1" do
    test "labels Copa do Brasil matches" do
      rows = [
        %{
          "round" => "1",
          "datetime" => "2012-03-07 16:00:00",
          "home_team" => "América - MG",
          "away_team" => "Boavista - RJ",
          "home_goal" => "0",
          "away_goal" => "0",
          "season" => "2012"
        }
      ]

      assert [m] = DataLoader.from_cup(rows)
      assert m.competition == "Copa do Brasil"
      assert m.home_team == "América"
    end
  end

  describe "from_libertadores/1" do
    test "captures the tournament stage" do
      rows = [
        %{
          "datetime" => "2013-02-12 20:15:00",
          "home_team" => "Nacional (URU)",
          "away_team" => "Barcelona-EQU",
          "home_goal" => "2",
          "away_goal" => "2",
          "season" => "2013",
          "stage" => "group stage"
        }
      ]

      assert [m] = DataLoader.from_libertadores(rows)
      assert m.competition == "Copa Libertadores"
      assert m.stage == "group stage"
      assert m.home_team == "Nacional"
    end
  end

  describe "from_br_football/1" do
    test "normalizes tournament names and float goals, infers season" do
      rows = [
        %{
          "tournament" => "Serie A",
          "home" => "Sao Paulo",
          "away" => "Flamengo",
          "home_goal" => "1.0",
          "away_goal" => "2.0",
          "date" => "2023-09-24",
          "time" => "20:00:00"
        }
      ]

      assert [m] = DataLoader.from_br_football(rows)
      assert m.competition == "Brasileirão Série A"
      assert m.home_goals == 1
      assert m.away_goals == 2
      assert m.season == 2023
    end
  end

  describe "from_historical/1" do
    test "maps Portuguese columns and Brazilian dates" do
      rows = [
        %{
          "Data" => "29/03/2003",
          "Ano" => "2003",
          "Rodada" => "1",
          "Equipe_mandante" => "Guarani",
          "Equipe_visitante" => "Vasco",
          "Gols_mandante" => "4",
          "Gols_visitante" => "2"
        }
      ]

      assert [m] = DataLoader.from_historical(rows)
      assert m.competition == "Brasileirão Série A"
      assert m.home_team == "Guarani"
      assert m.away_team == "Vasco"
      assert m.date == ~D[2003-03-29]
      assert m.home_goals == 4
    end
  end

  describe "players_from_fifa/1" do
    test "builds player structs" do
      rows = [%{"ID" => "1", "Name" => "X", "Nationality" => "Brazil", "Overall" => "80"}]
      assert [p] = DataLoader.players_from_fifa(rows)
      assert p.name == "X"
      assert p.overall == 80
    end
  end

  describe "dedup_matches/1" do
    test "removes exact-duplicate rows but keeps different scores" do
      a = BrazilianSoccer.Match.new(competition: "Brasileirão Série A", season: 2019, home_team: "Flamengo-RJ", away_team: "Santos-SP", home_goals: 2, away_goals: 0)
      dup = BrazilianSoccer.Match.new(competition: "Brasileirão Série A", season: 2019, home_team: "Flamengo-RJ", away_team: "Santos-SP", home_goals: 2, away_goals: 0)
      c = BrazilianSoccer.Match.new(competition: "Brasileirão Série A", season: 2019, home_team: "Flamengo-RJ", away_team: "Santos-SP", home_goals: 1, away_goals: 1)

      assert length(DataLoader.dedup_matches([a, dup, c])) == 2
    end
  end
end
