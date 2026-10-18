defmodule BrazilianSoccerMcp.DataLoaderTest do
  use ExUnit.Case, async: true

  alias BrazilianSoccerMcp.{DataLoader, Store, TeamName}

  setup_all do
    %{matches: matches, players: players} = Store.snapshot()
    %{matches: matches, players: players}
  end

  describe "Given the provided Kaggle datasets" do
    test "When loaded Then all three competitions are present", %{matches: matches} do
      competitions = matches |> Enum.map(& &1.competition) |> MapSet.new()

      assert MapSet.subset?(
               MapSet.new(["brasileirao", "copa_do_brasil", "libertadores"]),
               competitions
             )
    end

    test "When loaded Then overlapping copies across match files are merged", %{matches: matches} do
      # Raw rows total 23,954 (4,180 + 1,337 + 1,255 + 10,296 + 6,886). Overlaps must reduce that.
      assert length(matches) > 17_000
      assert length(matches) < 23_954
    end

    test "When loaded Then the FIFA player file is fully loaded", %{players: players} do
      assert length(players) > 18_000
    end

    test "When loaded Then every match has valid goals and a Date", %{matches: matches} do
      assert Enum.all?(matches, &(is_integer(&1.home_goals) and is_integer(&1.away_goals)))
      assert Enum.all?(matches, &match?(%Date{}, &1.date))
    end
  end

  describe "Given the historical DD/MM/YYYY date format" do
    test "When loaded Then a 2003 match is parsed with the correct date and score", %{
      matches: matches
    } do
      match =
        Enum.find(matches, fn m ->
          m.season == 2003 and TeamName.base(m.home_key) == "guarani" and
            TeamName.base(m.away_key) == "vasco"
        end)

      assert %{date: ~D[2003-03-29], home_goals: 4, away_goals: 2, competition: "brasileirao"} =
               match
    end
  end

  describe "Given a team written with a state suffix in one file and without it in another" do
    test "When loaded Then the state suffix becomes part of the team key", %{matches: matches} do
      keys = matches |> Enum.flat_map(&[&1.home_key, &1.away_key]) |> MapSet.new()

      assert MapSet.member?(keys, "flamengo|RJ")
      refute MapSet.member?(keys, "flamengo-RJ")
    end

    test "When a club has one state in the data Then its bare names are qualified with it", %{
      matches: matches
    } do
      keys = matches |> Enum.flat_map(&[&1.home_key, &1.away_key]) |> MapSet.new()

      assert MapSet.member?(keys, "palmeiras|SP")
      refute MapSet.member?(keys, "palmeiras")
    end
  end

  describe "Given two clubs that share a base name" do
    test "When loaded Then they keep separate keys", %{matches: matches} do
      keys = matches |> Enum.flat_map(&[&1.home_key, &1.away_key]) |> MapSet.new()

      assert MapSet.member?(keys, "atletico|MG")
      assert MapSet.member?(keys, "atletico|PR")
    end
  end

  describe "Given the FIFA player file" do
    test "When loaded Then a well-known Brazilian player is found with his rating", %{
      players: players
    } do
      neymar = Enum.find(players, &(&1.name == "Neymar Jr"))

      assert %{overall: 92, nationality: "Brazil", position: "LW"} = neymar
    end
  end

  describe "Given a directory with missing files" do
    test "When loading matches Then it raises rather than silently returning no data" do
      assert_raise File.Error, fn -> DataLoader.load_matches("does/not/exist") end
    end
  end
end
