defmodule BrasilSoccer.StoreTest do
  use ExUnit.Case, async: true

  alias BrasilSoccer.{Store, Fixtures}

  test "serves preloaded data and reports counts" do
    data = %{matches: Fixtures.matches(), players: Fixtures.players()}
    pid = start_supervised!({Store, name: :test_store, data: data})

    assert Store.matches(pid) == data.matches
    assert Store.players(pid) == data.players
    assert Store.stats(pid).matches == length(data.matches)
    assert Store.stats(pid).players == length(data.players)
  end

  test "loads from a data directory on demand" do
    dir = Path.join(System.tmp_dir!(), "store_#{System.unique_integer([:positive])}")
    File.mkdir_p!(dir)

    File.write!(Path.join(dir, "Brasileirao_Matches.csv"), """
    "datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
    2019-04-28 16:00:00,"Flamengo-RJ","RJ","Santos-SP","SP",2,0,2019,1
    """)

    on_exit(fn -> File.rm_rf!(dir) end)

    pid = start_supervised!({Store, name: :dir_store, dir: dir})
    assert length(Store.matches(pid)) == 1
    assert Store.players(pid) == []
  end
end
