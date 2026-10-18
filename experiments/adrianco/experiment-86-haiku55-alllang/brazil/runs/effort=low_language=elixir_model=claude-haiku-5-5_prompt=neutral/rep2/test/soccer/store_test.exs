defmodule SoccerMcp.StoreTest do
  # Feature: loading every dataset file into one searchable store
  use ExUnit.Case, async: true

  import ExUnit.CaptureIO

  alias SoccerMcp.{Match, Store}

  @fixtures Path.expand("../fixtures", __DIR__)

  setup_all do
    capture_io(:stderr, fn -> send(self(), {:store, Store.load(@fixtures)}) end)
    assert_received {:store, store}
    {:ok, store: store}
  end

  describe "Feature: loading all match files" do
    test "Scenario: every file is read and its matches are kept", %{store: store} do
      # Given the fixture copies of all six CSV files
      # When the store is loaded
      # Then every file contributes its played matches (counted before
      # de-duplication, so the overlap shows up in these numbers)
      sources = Map.new(store.sources)

      assert sources["Brasileirao_Matches.csv"] == 8
      assert sources["novo_campeonato_brasileiro.csv"] == 3
      assert sources["Brazilian_Cup_Matches.csv"] == 5
      assert sources["Libertadores_Matches.csv"] == 3
      assert sources["BR-Football-Dataset.csv"] == 3
      assert sources["fifa_data.csv"] == 7
    end

    test "Scenario: unplayed matches are skipped", %{store: store} do
      # Given a 2023 row with no scores (not yet played)
      # When the store is loaded
      # Then no match is recorded for that fixture
      refute Enum.any?(store.matches, &(&1.date == ~D[2023-03-01]))
    end

    test "Scenario: a match listed in two files is counted once", %{store: store} do
      # Given the 2019 Flamengo-Fluminense match appears in the Brasileirão
      # file and in the historical file
      # When the store is loaded
      # Then only one copy remains
      copies =
        Enum.count(store.matches, fn m ->
          m.date == ~D[2019-05-28] and m.home_key == "flamengo"
        end)

      assert copies == 1
    end

    test "Scenario: clubs that share a short name stay separate", %{store: store} do
      # Given Atlético-MG and Atlético-GO both play Flamengo in 2018
      # When the store is loaded
      # Then both matches are kept, because the states differ
      atletico_2018 =
        Enum.filter(store.matches, &(&1.season == 2018 and &1.home_key == "atletico"))

      assert Enum.map(atletico_2018, & &1.home_state) |> Enum.sort() == ["go", "mg"]
    end

    test "Scenario: team names with different suffixes are the same team", %{store: store} do
      # Given "4 de Julho EC - PI" in the cup file and "4 de Julho EC" in the extended file
      # When the store is loaded
      # Then the 2021 match is counted once and keeps the cup's display name
      matches = Enum.filter(store.matches, &(&1.date == ~D[2021-06-08]))

      assert [%Match{home: "São Paulo", away: "4 de Julho EC"}] = matches
    end
  end

  describe "Feature: competition labels" do
    test "Scenario: Copa do Brasil finals are labelled as finals", %{store: store} do
      # Given round 8 is the last round of the 2013 and 2021 cups
      # When the store is loaded
      # Then every round-8 match is labelled "final" and earlier rounds keep their number
      finals =
        store.matches
        |> Enum.filter(&(&1.competition == "Copa do Brasil" and &1.stage == "final"))
        |> Enum.map(& &1.season)

      assert Enum.sort(finals) == [2013, 2013, 2021]
      assert Enum.any?(store.matches, &(&1.stage == "Round 1"))
    end

    test "Scenario: the extended file's tournaments map to canonical names", %{store: store} do
      # Given "Serie B" in the extended file
      # When the store is loaded
      # Then the match is labelled Brasileirão Série B
      assert Enum.any?(store.matches, &(&1.competition == "Brasileirão Série B"))
    end
  end

  describe "Feature: player loading" do
    test "Scenario: FIFA rows become players with typed ratings", %{store: store} do
      # Given the FIFA fixture rows
      # When the store is loaded
      # Then ratings are integers and text fields are present
      messi = Enum.find(store.players, &(&1.name == "L. Messi"))

      assert messi.overall == 94
      assert messi.nationality == "Argentina"
      assert messi.club == "FC Barcelona"
      assert messi.position == "RF"
    end
  end
end
