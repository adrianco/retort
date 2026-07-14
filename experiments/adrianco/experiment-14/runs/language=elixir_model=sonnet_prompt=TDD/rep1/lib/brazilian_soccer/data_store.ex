defmodule BrazilianSoccer.DataStore do
  use GenServer
  require Logger

  alias BrazilianSoccer.DataLoader

  @table_matches :bs_matches
  @table_players :bs_players

  def start_link(_opts) do
    GenServer.start_link(__MODULE__, [], name: __MODULE__)
  end

  def matches, do: :ets.tab2list(@table_matches) |> Enum.map(fn {_k, v} -> v end)
  def players, do: :ets.tab2list(@table_players) |> Enum.map(fn {_k, v} -> v end)

  @impl true
  def init(_) do
    :ets.new(@table_matches, [:named_table, :public, :bag])
    :ets.new(@table_players, [:named_table, :public, :set])
    load_data()
    {:ok, %{}}
  end

  defp load_data do
    data_dir = Application.get_env(:brazilian_soccer, :data_dir, "data/kaggle")
    load_matches(data_dir)
    load_players(data_dir)
  end

  defp load_matches(data_dir) do
    files = [
      {Path.join(data_dir, "Brasileirao_Matches.csv"), :brasileirao},
      {Path.join(data_dir, "Brazilian_Cup_Matches.csv"), :cup},
      {Path.join(data_dir, "Libertadores_Matches.csv"), :libertadores},
      {Path.join(data_dir, "novo_campeonato_brasileiro.csv"), :historico},
      {Path.join(data_dir, "BR-Football-Dataset.csv"), :br_football}
    ]

    Enum.each(files, fn {path, type} ->
      if File.exists?(path) do
        count = load_match_file(path, type)
        Logger.info("Loaded #{count} matches from #{Path.basename(path)}")
      else
        Logger.warning("Data file not found: #{path}")
      end
    end)
  end

  defp load_match_file(path, type) do
    path
    |> File.stream!()
    |> NimbleCSV.RFC4180.parse_stream(skip_headers: true)
    |> Stream.map(fn row ->
      case type do
        :brasileirao -> DataLoader.parse_brasileirao_row(row)
        :cup -> DataLoader.parse_cup_row(row)
        :libertadores -> DataLoader.parse_libertadores_row(row)
        :historico -> DataLoader.parse_historico_row(row)
        :br_football -> DataLoader.parse_br_football_row(row)
      end
    end)
    |> Stream.reject(&is_nil/1)
    |> Stream.with_index()
    |> Enum.reduce(0, fn {match, idx}, acc ->
      key = {type, idx}
      :ets.insert(@table_matches, {key, match})
      acc + 1
    end)
  rescue
    e ->
      Logger.error("Failed to load #{path}: #{inspect(e)}")
      0
  end

  defp load_players(data_dir) do
    path = Path.join(data_dir, "fifa_data.csv")

    if File.exists?(path) do
      count =
        path
        |> File.stream!()
        |> NimbleCSV.RFC4180.parse_stream(skip_headers: true)
        |> Stream.map(&DataLoader.parse_player_row/1)
        |> Stream.reject(&is_nil/1)
        |> Enum.reduce(0, fn player, acc ->
          :ets.insert(@table_players, {player.id, player})
          acc + 1
        end)

      Logger.info("Loaded #{count} players from fifa_data.csv")
    else
      Logger.warning("Player data file not found: #{path}")
    end
  end
end
