defmodule BrazilianSoccer.DataLoader do
  @moduledoc """
  Loads the Kaggle CSV files into normalized `Match` and `Player` structs.

  Each source file has its own column layout; the `from_*` functions translate a
  list of CSV row-maps (keyed by header) into unified `Match` structs. `load!/1`
  reads every file from a directory and returns a populated `Dataset`,
  deduplicating matches that appear in more than one source.
  """

  alias BrazilianSoccer.{CSV, Dataset, Match, Player}

  @files %{
    brasileirao: "Brasileirao_Matches.csv",
    cup: "Brazilian_Cup_Matches.csv",
    libertadores: "Libertadores_Matches.csv",
    br_football: "BR-Football-Dataset.csv",
    historical: "novo_campeonato_brasileiro.csv",
    fifa: "fifa_data.csv"
  }

  @doc "Default directory holding the Kaggle CSV files."
  @spec default_dir() :: String.t()
  def default_dir, do: Path.join(["data", "kaggle"])

  @doc """
  Load all CSV files from `dir` and return a `Dataset`. Missing files are
  skipped (with the corresponding collection left empty).
  """
  @spec load!(String.t()) :: Dataset.t()
  def load!(dir \\ default_dir()) do
    matches =
      [
        {:brasileirao, &from_brasileirao/1},
        {:cup, &from_cup/1},
        {:libertadores, &from_libertadores/1},
        {:br_football, &from_br_football/1},
        {:historical, &from_historical/1}
      ]
      |> Enum.flat_map(fn {key, fun} -> dir |> read_maps(key) |> fun.() end)
      |> dedup_matches()

    players = dir |> read_maps(:fifa) |> players_from_fifa()

    Dataset.new(matches, players)
  end

  defp read_maps(dir, key) do
    path = Path.join(dir, @files[key])

    case File.read(path) do
      {:ok, content} -> CSV.parse_to_maps(content)
      {:error, _} -> []
    end
  end

  @doc "Map `Brasileirao_Matches.csv` rows to matches."
  @spec from_brasileirao([map()]) :: [Match.t()]
  def from_brasileirao(rows) do
    Enum.map(rows, fn r ->
      Match.new(
        competition: "Brasileirão Série A",
        source: "Brasileirao_Matches.csv",
        date: r["datetime"],
        home_team: r["home_team"],
        away_team: r["away_team"],
        home_goals: r["home_goal"],
        away_goals: r["away_goal"],
        season: r["season"],
        round: r["round"]
      )
    end)
  end

  @doc "Map `Brazilian_Cup_Matches.csv` rows to matches."
  @spec from_cup([map()]) :: [Match.t()]
  def from_cup(rows) do
    Enum.map(rows, fn r ->
      Match.new(
        competition: "Copa do Brasil",
        source: "Brazilian_Cup_Matches.csv",
        date: r["datetime"],
        home_team: r["home_team"],
        away_team: r["away_team"],
        home_goals: r["home_goal"],
        away_goals: r["away_goal"],
        season: r["season"],
        round: r["round"]
      )
    end)
  end

  @doc "Map `Libertadores_Matches.csv` rows to matches."
  @spec from_libertadores([map()]) :: [Match.t()]
  def from_libertadores(rows) do
    Enum.map(rows, fn r ->
      Match.new(
        competition: "Copa Libertadores",
        source: "Libertadores_Matches.csv",
        date: r["datetime"],
        home_team: r["home_team"],
        away_team: r["away_team"],
        home_goals: r["home_goal"],
        away_goals: r["away_goal"],
        season: r["season"],
        stage: r["stage"]
      )
    end)
  end

  @doc "Map `BR-Football-Dataset.csv` rows to matches."
  @spec from_br_football([map()]) :: [Match.t()]
  def from_br_football(rows) do
    Enum.map(rows, fn r ->
      Match.new(
        competition: normalize_tournament(r["tournament"]),
        source: "BR-Football-Dataset.csv",
        date: r["date"],
        home_team: r["home"],
        away_team: r["away"],
        home_goals: r["home_goal"],
        away_goals: r["away_goal"]
      )
    end)
  end

  @doc "Map `novo_campeonato_brasileiro.csv` rows to matches."
  @spec from_historical([map()]) :: [Match.t()]
  def from_historical(rows) do
    Enum.map(rows, fn r ->
      Match.new(
        competition: "Brasileirão Série A",
        source: "novo_campeonato_brasileiro.csv",
        date: r["Data"],
        home_team: r["Equipe_mandante"],
        away_team: r["Equipe_visitante"],
        home_goals: r["Gols_mandante"],
        away_goals: r["Gols_visitante"],
        season: r["Ano"],
        round: r["Rodada"]
      )
    end)
  end

  @doc "Build player structs from `fifa_data.csv` rows."
  @spec players_from_fifa([map()]) :: [Player.t()]
  def players_from_fifa(rows), do: Enum.map(rows, &Player.from_row/1)

  @doc """
  Remove matches that are duplicated across source files, keying on competition,
  season, normalized team names and the score.
  """
  @spec dedup_matches([Match.t()]) :: [Match.t()]
  def dedup_matches(matches) do
    matches
    |> Enum.reduce({[], MapSet.new()}, fn m, {acc, seen} ->
      key = dedup_key(m)

      if MapSet.member?(seen, key) do
        {acc, seen}
      else
        {[m | acc], MapSet.put(seen, key)}
      end
    end)
    |> elem(0)
    |> Enum.reverse()
  end

  defp dedup_key(%Match{} = m) do
    {m.competition, m.season, m.home_key, m.away_key, m.home_goals, m.away_goals}
  end

  defp normalize_tournament(nil), do: nil

  defp normalize_tournament(name) do
    case String.trim(name) do
      "Serie A" -> "Brasileirão Série A"
      "Serie B" -> "Brasileirão Série B"
      "Serie C" -> "Brasileirão Série C"
      "Copa do Brasil" -> "Copa do Brasil"
      other -> other
    end
  end
end
