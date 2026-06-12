defmodule BrSoccer.Repo do
  @moduledoc """
  In-memory store for the loaded datasets.

  CSVs are parsed once at start-up and cached for the lifetime of the process,
  so every query is a fast in-memory scan over plain lists. A read-through
  cache via `:persistent_term` keeps reads lock-free and lets query modules run
  without round-tripping through the GenServer.
  """

  use GenServer

  alias BrSoccer.Loader

  @pt_key {__MODULE__, :data}

  # ---- public API ----

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @doc "All match records."
  def matches, do: data().matches

  @doc "All player records."
  def players, do: data().players

  @doc "The set of canonical team keys that appear in the match data (i.e. Brazilian/relevant clubs)."
  def team_keys, do: data().team_keys

  @doc "Replace the cached data (used by tests to load fixtures)."
  def put_data(%{matches: _, players: _} = data) do
    :persistent_term.put(@pt_key, index(data))
    :ok
  end

  @doc "Force a reload from disk."
  def reload do
    put_data(Loader.load_all())
  end

  defp data do
    case :persistent_term.get(@pt_key, nil) do
      nil ->
        d = index(Loader.load_all())
        :persistent_term.put(@pt_key, d)
        d

      d ->
        d
    end
  end

  defp index(%{matches: matches, players: players}) do
    keys =
      matches
      |> Enum.flat_map(&[&1.home_key, &1.away_key])
      |> MapSet.new()

    %{matches: matches, players: players, team_keys: keys}
  end

  # ---- GenServer ----

  @impl true
  def init(_opts) do
    # Warm the cache eagerly so the first query is fast.
    _ = data()
    {:ok, %{}}
  end
end
