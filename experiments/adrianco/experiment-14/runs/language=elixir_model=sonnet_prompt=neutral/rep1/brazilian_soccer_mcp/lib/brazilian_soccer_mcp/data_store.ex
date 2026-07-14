defmodule BrazilianSoccerMcp.DataStore do
  @moduledoc """
  GenServer that holds all CSV data in memory for fast querying.
  """
  use GenServer

  alias BrazilianSoccerMcp.DataLoader

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def get_all_matches do
    GenServer.call(__MODULE__, :get_all_matches, 30_000)
  end

  def get_brasileirao do
    GenServer.call(__MODULE__, :get_brasileirao, 30_000)
  end

  def get_copa_brasil do
    GenServer.call(__MODULE__, :get_copa_brasil, 30_000)
  end

  def get_libertadores do
    GenServer.call(__MODULE__, :get_libertadores, 30_000)
  end

  def get_extended do
    GenServer.call(__MODULE__, :get_extended, 30_000)
  end

  def get_historical do
    GenServer.call(__MODULE__, :get_historical, 30_000)
  end

  def get_players do
    GenServer.call(__MODULE__, :get_players, 30_000)
  end

  @impl true
  def init(_opts) do
    IO.puts(:stderr, "Loading Brazilian soccer data...")
    data = DataLoader.load_all()
    # Brasileirao_Matches.csv covers 2012+, historical covers 2003-2019.
    # To avoid duplicates in all_matches, use historical only for pre-2012 seasons.
    historical_pre2012 = Enum.filter(data.historical, fn m ->
      is_nil(m.season) or m.season < 2012
    end)
    all_matches = data.brasileirao ++ data.copa_brasil ++ data.libertadores ++
                  data.extended ++ historical_pre2012
    IO.puts(:stderr, "Data loaded: #{length(all_matches)} matches, #{length(data.players)} players")

    {:ok, Map.put(data, :all_matches, all_matches)}
  end

  @impl true
  def handle_call(:get_all_matches, _from, state), do: {:reply, state.all_matches, state}
  def handle_call(:get_brasileirao, _from, state), do: {:reply, state.brasileirao, state}
  def handle_call(:get_copa_brasil, _from, state), do: {:reply, state.copa_brasil, state}
  def handle_call(:get_libertadores, _from, state), do: {:reply, state.libertadores, state}
  def handle_call(:get_extended, _from, state), do: {:reply, state.extended, state}
  def handle_call(:get_historical, _from, state), do: {:reply, state.historical, state}
  def handle_call(:get_players, _from, state), do: {:reply, state.players, state}
end
