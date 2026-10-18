defmodule BrazilianSoccerMcp.Store do
  @moduledoc """
  Holds the loaded datasets in memory. The CSVs are parsed once at startup,
  and every query reads from this process's state.
  """

  use GenServer

  alias BrazilianSoccerMcp.DataLoader

  @doc "Starts the store, loading all CSV files from `data_dir`."
  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @doc "Returns `%{matches: [...], players: [...]}`."
  @spec snapshot(GenServer.server()) :: %{matches: list(), players: list()}
  def snapshot(server \\ __MODULE__), do: GenServer.call(server, :snapshot, 60_000)

  @impl true
  def init(opts) do
    dir = Keyword.fetch!(opts, :data_dir)

    {:ok,
     %{
       matches: DataLoader.load_matches(dir),
       players: DataLoader.load_players(dir)
     }}
  end

  @impl true
  def handle_call(:snapshot, _from, state), do: {:reply, state, state}
end
