defmodule BrSoccer.IntegrationTest do
  @moduledoc """
  End-to-end tests against the real Kaggle CSVs in `data/kaggle/`.

  These verify the success criteria: all six files load, cross-file queries
  work, and known historical facts come out correctly.
  """
  use ExUnit.Case, async: false

  alias BrSoccer.{Competitions, Loader, Matches, Players, Repo, Stats}

  setup_all do
    Repo.reload()
    :ok
  end

  test "all six CSV files load into matches and players" do
    assert length(Repo.players()) == 18_207
    # Every match source is represented after loading + de-duplication.
    sources = Repo.matches() |> Enum.map(& &1.source) |> Enum.uniq() |> MapSet.new()

    assert MapSet.subset?(
             MapSet.new([:brasileirao_csv, :cup_csv, :libertadores_csv, :br_football, :novo]),
             sources
           )
  end

  test "each individual file is parseable and non-empty" do
    dir = Loader.data_dir()

    for file <- ~w(Brasileirao_Matches.csv Brazilian_Cup_Matches.csv Libertadores_Matches.csv
                   BR-Football-Dataset.csv novo_campeonato_brasileiro.csv fifa_data.csv) do
      rows = BrSoccer.CSV.parse_file(Path.join(dir, file))
      assert length(rows) > 100, "expected data rows in #{file}"
    end
  end

  test "2019 Brasileirão champion is Flamengo with 90 points" do
    table = Competitions.standings(:brasileirao, 2019)
    champ = hd(table)
    assert champ.team == "Flamengo"
    assert champ.points == 90
    assert length(table) == 20
  end

  test "2022 Brasileirão (single-source season) computes a 20-team table" do
    table = Competitions.standings(:brasileirao, 2022)
    assert length(table) == 20
    assert hd(table).position == 1
  end

  test "head-to-head works for a classic rivalry" do
    h = Matches.head_to_head("Flamengo", "Fluminense")
    assert h.total > 20
    assert h.a_wins + h.b_wins + h.draws == h.played
  end

  test "team can be found via name variations across files" do
    # Palmeiras appears as 'Palmeiras', 'Palmeiras-SP' across files; all should resolve.
    comps = Matches.competitions_for("Palmeiras") |> Enum.map(& &1.competition)
    assert :brasileirao in comps
    assert :libertadores in comps
  end

  test "Brazilian players can be filtered and the dataset has the expected scale" do
    brazilians = Players.brazilians()
    assert length(brazilians) == 827
    assert hd(brazilians).nationality == "Brazil"
    # Highest-rated Brazilian should be a world-class name.
    assert hd(brazilians).overall >= 88
  end

  test "cross-file query: Brazilian players grouped by Brazilian clubs" do
    groups = Players.brazilians_at_brazilian_clubs(min_count: 5)
    assert length(groups) > 3
    assert Enum.all?(groups, &(&1.avg_overall > 0))
    # Clubs identified here must exist in the match data.
    keys = Repo.team_keys()
    assert Enum.all?(groups, &MapSet.member?(keys, &1.key))
  end

  test "aggregate stats over the whole Brasileirão are sane" do
    s = Stats.summary(competition: :brasileirao)
    assert s.matches > 4000
    assert s.avg_goals > 2.0 and s.avg_goals < 3.5
    assert s.home_win_rate > 40.0 and s.home_win_rate < 60.0
  end

  test "simple lookups respond well under the 2s budget" do
    {micros, _} = :timer.tc(fn -> Matches.head_to_head("Flamengo", "Corinthians") end)
    assert micros < 2_000_000
  end

  test "aggregate queries respond under the 5s budget" do
    {micros, _} = :timer.tc(fn -> Competitions.standings(:brasileirao, 2019) end)
    assert micros < 5_000_000
  end
end
