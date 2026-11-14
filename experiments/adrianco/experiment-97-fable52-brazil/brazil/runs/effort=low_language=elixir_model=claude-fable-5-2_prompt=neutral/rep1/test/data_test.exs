defmodule BrazilianSoccer.DataTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.{Data, Queries}

  setup_all do
    {:ok, data: Data.get()}
  end

  describe "Feature: data loading" do
    test "Scenario: all six CSV files are loaded", %{data: d} do
      # Given the Kaggle files / When the data is loaded / Then every file contributes rows
      assert d.files.brasileirao.rows == 4180
      assert d.files.cup.rows == 1337
      assert d.files.libertadores.rows == 1255
      assert d.files.br_football.rows == 10296
      assert d.files.historical.rows == 6886
      assert d.files.fifa.rows == 18207
      assert length(d.players) == 18207

      for src <- [:brasileirao, :cup, :libertadores, :br_football, :historical] do
        assert Enum.any?(d.matches, &(src in &1.sources)), "no matches from #{src}"
      end
    end

    test "Scenario: every match has date, teams, score and competition", %{data: d} do
      for m <- d.matches do
        assert %Date{} = m.date
        assert is_integer(m.home_goals) and is_integer(m.away_goals)
        assert is_binary(m.home_name) and is_binary(m.away_name)
        assert m.competition in Data.competitions()
        assert is_integer(m.season)
      end
    end

    test "Scenario: the same fixture from several files is merged, not double counted", %{data: d} do
      serie_a = Enum.filter(d.matches, &(&1.competition == "Brasileirão Série A"))

      # 20 teams, double round robin => 380 matches per season
      for season <- 2006..2022 do
        assert Enum.count(serie_a, &(&1.season == season)) == 380, "season #{season}"
      end

      # a 2019 match is known to three files and keeps the detail of each
      m =
        Enum.find(serie_a, &(&1.season == 2019 and &1.home == "flamengo" and &1.away == "gremio"))

      assert Enum.sort(m.sources) == [:br_football, :brasileirao, :historical]
      assert {m.home_goals, m.away_goals} == {3, 1}
      assert m.date == ~D[2019-08-10]
      assert m.round != nil and m.arena != nil and m.stats[:home_corners] != nil
    end

    test "Scenario: UTF-8 names keep their accents", %{data: d} do
      assert d.teams["gremio"].name == "Grêmio"
      assert d.teams["sao paulo"].name == "São Paulo"
      assert d.teams["avai"].name == "Avaí"
      assert Enum.any?(d.players, &(&1.club == "Grêmio"))
      refute Enum.any?(d.matches, &(&1.home == &1.away))
    end

    test "Scenario: team name variations resolve to one team", %{data: d} do
      for {variants, key} <- [
            {["Flamengo", "Flamengo-RJ", "flamengo", "Clube de Regatas do Flamengo"], "flamengo"},
            {["São Paulo", "Sao Paulo", "São Paulo FC", "Sao Paulo-SP"], "sao paulo"},
            {["Atlético-MG", "Atletico Mineiro", "Atlético Mineiro"], "atletico"},
            {["Athletico-PR", "Atlético Paranaense", "Athletico Paranaense"], "atletico-pr"},
            {["Vasco", "Vasco da Gama"], "vasco"},
            {["Sport Club Corinthians Paulista", "Corinthians"], "corinthians"}
          ],
          v <- variants do
        assert Queries.resolve_team(d, v) == {:ok, key}, v
      end

      assert {:ok, "flamengo-pi"} = Queries.resolve_team(d, "Flamengo-PI")
      assert {:error, _} = Queries.resolve_team(d, "Nowhere United")
    end
  end
end
