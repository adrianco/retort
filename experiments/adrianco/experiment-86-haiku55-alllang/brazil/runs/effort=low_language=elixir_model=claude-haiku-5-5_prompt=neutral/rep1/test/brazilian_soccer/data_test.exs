defmodule BrazilianSoccer.DataTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccer.Data

  @fixtures Path.expand("../fixtures/kaggle", __DIR__)
  @real_dir Path.expand("../../data/kaggle", __DIR__)

  setup_all do
    %{data: Data.load(@fixtures)}
  end

  describe "Scenario: all match files are merged" do
    test "Given all six files, then matches from every source are present", %{data: data} do
      sources = data.matches |> Enum.map(& &1.source) |> Enum.uniq() |> Enum.sort()

      assert sources == [
               "BR-Football-Dataset.csv",
               "Brasileirao_Matches.csv",
               "Brazilian_Cup_Matches.csv",
               "Libertadores_Matches.csv",
               "novo_campeonato_brasileiro.csv"
             ]
    end

    test "Given the same match in two files, then it is kept once", %{data: data} do
      corinthians_palmeiras =
        Enum.filter(data.matches, fn m ->
          m.date == ~D[2022-04-10] and m.home_key == "corinthians"
        end)

      assert [%{source: "Brasileirao_Matches.csv"}] = corinthians_palmeiras
    end

    test "Given a duplicate whose date differs by a day, then it is still dropped", %{data: data} do
      refute Enum.any?(data.matches, &(&1.date == ~D[2022-04-11]))
    end

    test "Given a row with no goals, then it is skipped", %{data: data} do
      refute Enum.any?(data.matches, &(&1.date == ~D[2003-03-30]))
    end

    test "Given the fixtures, then there are 14 matches in total", %{data: data} do
      assert length(data.matches) == 14
    end

    test "Given Brazilian-format and ISO dates, then both become Date structs", %{data: data} do
      assert Enum.any?(data.matches, &(&1.date == ~D[2003-03-29]))
      assert Enum.any?(data.matches, &(&1.date == ~D[2023-09-03]))
    end
  end

  describe "Scenario: competition and stage labels" do
    test "Given the Brasileirão file, then rounds are labelled and the competition is Série A", %{
      data: data
    } do
      flu = Enum.find(data.matches, &(&1.date == ~D[2023-09-03] and &1.source =~ "Brasileirao"))
      assert flu.competition == "Brasileirão Série A"
      assert flu.stage == "Round 22"
    end

    test "Given the cup file, then the final keeps its stage name", %{data: data} do
      final = Enum.find(data.matches, &(&1.stage == "final"))
      assert final.competition == "Copa do Brasil"
      assert final.home == "Flamengo"
    end

    test "Given BR-Football tournament codes, then they map to Brazilian names", %{data: data} do
      assert Enum.any?(data.matches, &(&1.competition == "Brasileirão Série B"))
    end
  end

  describe "Scenario: player data" do
    test "Given the FIFA file, then players are loaded with typed ratings", %{data: data} do
      messi = Enum.find(data.players, &(&1.name == "L. Messi"))
      assert messi.overall == 94
      assert messi.position == "RF"
      assert messi.nationality == "Argentina"
      assert length(data.players) == 7
    end
  end

  describe "Scenario: the real Kaggle files" do
    @tag :real_data
    test "Given data/kaggle, then all six files load" do
      if File.dir?(@real_dir) do
        data = Data.load(@real_dir)

        assert length(data.players) == 18_207

        competitions = data.matches |> Enum.map(& &1.competition) |> MapSet.new()

        assert MapSet.subset?(
                 MapSet.new(["Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"]),
                 competitions
               )

        assert length(data.matches) > 15_000
      end
    end
  end
end
