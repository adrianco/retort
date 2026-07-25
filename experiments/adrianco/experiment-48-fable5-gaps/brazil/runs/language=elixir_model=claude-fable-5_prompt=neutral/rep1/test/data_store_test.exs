defmodule BrazilianSoccerMcp.DataStoreTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccerMcp.DataStore

  describe "Given the six CSV files, when the data store is loaded" do
    test "then all match files contribute records" do
      sources = DataStore.matches() |> Enum.frequencies_by(& &1.source)

      # Raw file row counts: serie_a 4180, historical 6886, copa 1337,
      # libertadores 1255, extended 10296. After cross-file deduplication each
      # source must still be represented.
      for source <- [:serie_a, :historical, :copa, :libertadores, :extended] do
        assert Map.get(sources, source, 0) > 0, "expected records from #{source}"
      end
    end

    test "then duplicated coverage across files is collapsed" do
      matches = DataStore.matches()
      # 24 954 raw match rows across the five files shrink after dedup.
      assert length(matches) < 20_000
      assert length(matches) > 15_000

      # A regular 20-team Série A season has exactly 380 matches even though
      # three files cover it.
      per_season = fn s ->
        Enum.count(matches, &(&1.competition == :brasileirao and &1.season == s))
      end

      assert per_season.(2015) == 380
      assert per_season.(2018) == 380
      assert per_season.(2019) == 380
    end

    test "then all FIFA players are loaded" do
      assert length(DataStore.players()) == 18_207
    end

    test "then every match has a date and canonical team keys" do
      assert Enum.all?(DataStore.matches(), fn m ->
               match?(%Date{}, m.date) and is_binary(m.home_key) and is_binary(m.away_key)
             end)
    end

    test "then multiple date formats were parsed" do
      # ISO datetime (2012+), Brazilian DD/MM/YYYY (2003-2011), ISO date (extended)
      years = DataStore.matches() |> Enum.map(& &1.date.year) |> MapSet.new()
      assert 2003 in years
      assert 2012 in years
      assert 2023 in years
    end

    test "then UTF-8 team names are preserved" do
      displays = DataStore.teams() |> Map.values() |> Enum.map(& &1.display)
      assert "São Paulo" in displays
      assert "Grêmio" in displays
      assert "Avaí" in displays
    end

    test "then famous clubs display without state suffix but namesakes keep it" do
      assert DataStore.display("flamengo-rj") == "Flamengo"
      assert DataStore.display("america-mg") == "América-MG"
      assert DataStore.display("america-rn") == "América-RN"
    end

    test "then date parsing helpers accept all dataset formats" do
      assert DataStore.parse_date("2023-09-24") == ~D[2023-09-24]
      assert DataStore.parse_date("2012-05-19 18:30:00") == ~D[2012-05-19]
      assert DataStore.parse_date("29/03/2003") == ~D[2003-03-29]
      assert DataStore.parse_date("not a date") == nil
    end

    test "then lenient integer parsing handles dataset number styles" do
      assert DataStore.parse_int("2") == 2
      assert DataStore.parse_int("1.0") == 1
      assert DataStore.parse_int("88+2") == 88
      assert DataStore.parse_int("") == nil
    end
  end
end
