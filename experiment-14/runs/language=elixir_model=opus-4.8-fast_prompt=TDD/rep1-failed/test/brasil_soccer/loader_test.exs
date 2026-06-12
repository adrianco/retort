defmodule BrasilSoccer.LoaderTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.Loader

  describe "parse_date/1" do
    test "parses ISO datetime with time" do
      assert Loader.parse_date("2012-05-19 18:30:00") == ~D[2012-05-19]
    end

    test "parses ISO date" do
      assert Loader.parse_date("2023-09-24") == ~D[2023-09-24]
    end

    test "parses Brazilian DD/MM/YYYY" do
      assert Loader.parse_date("29/03/2003") == ~D[2003-03-29]
    end

    test "returns nil for blank or unparseable values" do
      assert Loader.parse_date("") == nil
      assert Loader.parse_date("not a date") == nil
    end
  end

  describe "to_int/1" do
    test "parses integers and floats-as-strings" do
      assert Loader.to_int("3") == 3
      assert Loader.to_int("2.0") == 2
    end

    test "returns nil for blanks" do
      assert Loader.to_int("") == nil
      assert Loader.to_int("NA") == nil
    end
  end

  describe "brasileirao/1" do
    test "maps rows to matches tagged with the Brasileirão competition" do
      rows = [
        %{
          "datetime" => "2012-05-19 18:30:00",
          "home_team" => "Palmeiras-SP",
          "home_team_state" => "SP",
          "away_team" => "Portuguesa-SP",
          "away_team_state" => "SP",
          "home_goal" => "1",
          "away_goal" => "1",
          "season" => "2012",
          "round" => "1"
        }
      ]

      assert [m] = Loader.brasileirao(rows)
      assert m.competition == "Brasileirão"
      assert m.home_team == "Palmeiras"
      assert m.season == 2012
      assert m.round == "1"
      assert m.date == ~D[2012-05-19]
      assert m.home_state == "SP"
      assert m.winner == :draw
    end
  end

  describe "libertadores/1" do
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

      assert [m] = Loader.libertadores(rows)
      assert m.competition == "Libertadores"
      assert m.stage == "group stage"
      assert m.home_team == "Nacional"
    end
  end

  describe "novo/1" do
    test "maps Portuguese columns and DD/MM/YYYY dates" do
      rows = [
        %{
          "Data" => "29/03/2003",
          "Ano" => "2003",
          "Rodada" => "1",
          "Equipe_mandante" => "Guarani",
          "Equipe_visitante" => "Vasco",
          "Gols_mandante" => "4",
          "Gols_visitante" => "2",
          "Mandante_UF" => "SP",
          "Visitante_UF" => "RJ",
          "Arena" => "Brinco de Ouro"
        }
      ]

      assert [m] = Loader.novo(rows)
      assert m.competition == "Brasileirão"
      assert m.season == 2003
      assert m.date == ~D[2003-03-29]
      assert m.home_team == "Guarani"
      assert m.winner == :home
    end
  end

  describe "br_football/1" do
    test "uses the tournament column as competition" do
      rows = [
        %{
          "tournament" => "Copa do Brasil",
          "home" => "Sao Paulo",
          "away" => "Flamengo",
          "home_goal" => "1.0",
          "away_goal" => "1.0",
          "date" => "2023-09-24"
        }
      ]

      assert [m] = Loader.br_football(rows)
      assert m.competition == "Copa do Brasil"
      assert m.home_goal == 1
      assert m.date == ~D[2023-09-24]
    end
  end

  describe "players/1" do
    test "extracts and types the player fields" do
      rows = [
        %{
          "ID" => "158023",
          "Name" => "L. Messi",
          "Age" => "31",
          "Nationality" => "Argentina",
          "Overall" => "94",
          "Potential" => "94",
          "Club" => "FC Barcelona",
          "Position" => "RF"
        }
      ]

      assert [p] = Loader.players(rows)
      assert p.name == "L. Messi"
      assert p.overall == 94
      assert p.age == 31
      assert p.nationality == "Argentina"
      assert p.club == "FC Barcelona"
      assert p.position == "RF"
    end
  end
end
