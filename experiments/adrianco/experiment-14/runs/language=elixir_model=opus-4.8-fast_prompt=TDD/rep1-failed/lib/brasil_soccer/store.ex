defmodule BrasilSoccer.Store do
  @moduledoc """
  Holds the loaded match and player datasets in memory so the CSV files are
  parsed once at start-up rather than on every query.

  Start it with either preloaded `:data` (a `%{matches:, players:}` map, handy
  for tests) or a `:dir` to load from. With neither, it falls back to the
  `:data_dir` application environment, defaulting to `data/kaggle`.
  """

  use GenServer

  alias BrasilSoccer.Loader

  @default_dir "data/kaggle"

  # ── Client API ────────────────────────────────────────────────────────────

  def start_link(opts) do
    {name, opts} = Keyword.pop(opts, :name, __MODULE__)
    GenServer.start_link(__MODULE__, opts, name: name)
  end

  @doc "All loaded matches."
  def matches(server \\ __MODULE__), do: GenServer.call(server, :matches)

  @doc "All loaded players."
  def players(server \\ __MODULE__), do: GenServer.call(server, :players)

  @doc "Counts and basic coverage information."
  def stats(server \\ __MODULE__), do: GenServer.call(server, :stats)

  # ── Server callbacks ──────────────────────────────────────────────────────

  @impl true
  def init(opts) do
    data =
      case Keyword.fetch(opts, :data) do
        {:ok, data} -> data
        :error -> Loader.load_dir(dir(opts))
      end

    {:ok, data}
  end

  defp dir(opts) do
    Keyword.get(opts, :dir) ||
      Application.get_env(:brasil_soccer, :data_dir, @default_dir)
  end

  @impl true
  def handle_call(:matches, _from, data), do: {:reply, data.matches, data}
  def handle_call(:players, _from, data), do: {:reply, data.players, data}

  def handle_call(:stats, _from, data) do
    competitions =
      data.matches
      |> Enum.map(& &1.competition)
      |> Enum.reject(&is_nil/1)
      |> Enum.uniq()
      |> Enum.sort()

    stats = %{
      matches: length(data.matches),
      players: length(data.players),
      competitions: competitions
    }

    {:reply, stats, data}
  end
end
