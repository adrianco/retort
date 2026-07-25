defmodule BrazilianSoccer.Repo do
  @moduledoc """
  Loads the knowledge graph once and hands it out for free afterwards.

  The parsed graph lives in `:persistent_term`, so queries read it without
  copying or messaging.  Building it takes a couple of seconds, so the result
  is also memoised on disk (keyed by the size+mtime of every CSV); a warm start
  is a single `:erlang.binary_to_term/1`.

  A `GenServer` serialises the (re)build, which means concurrent first callers
  wait for one build instead of racing to do the same work.
  """

  use GenServer

  require Logger

  alias BrazilianSoccer.Config
  alias BrazilianSoccer.Data.Graph

  @term_key {__MODULE__, :graph}
  @cache_version 3

  # --- client --------------------------------------------------------------

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @doc "The knowledge graph, loading it on first use."
  @spec graph() :: Graph.t()
  def graph do
    case :persistent_term.get(@term_key, nil) do
      nil -> load()
      graph -> graph
    end
  end

  @doc "True once the graph is in memory."
  @spec loaded?() :: boolean
  def loaded?, do: :persistent_term.get(@term_key, nil) != nil

  @doc "Force a rebuild from the CSV files, ignoring the on-disk cache."
  @spec reload() :: Graph.t()
  def reload do
    if Process.whereis(__MODULE__) do
      GenServer.call(__MODULE__, {:load, true}, :infinity)
    else
      do_load(true)
    end
  end

  @doc "Replace the in-memory graph (used by tests to inject fixtures)."
  @spec put(Graph.t()) :: :ok
  def put(%Graph{} = graph), do: :persistent_term.put(@term_key, graph)

  @doc "Drop the in-memory graph."
  @spec clear() :: :ok
  def clear do
    :persistent_term.erase(@term_key)
    :ok
  end

  defp load do
    if Process.whereis(__MODULE__) do
      GenServer.call(__MODULE__, {:load, false}, :infinity)
    else
      do_load(false)
    end
  end

  # --- server --------------------------------------------------------------

  @impl true
  def init(opts) do
    if Keyword.get(opts, :eager, false), do: send(self(), :load)
    {:ok, %{}}
  end

  @impl true
  def handle_call({:load, force}, _from, state) do
    cached = :persistent_term.get(@term_key, nil)
    graph = if force or is_nil(cached), do: do_load(force), else: cached
    {:reply, graph, state}
  end

  @impl true
  def handle_info(:load, state) do
    if :persistent_term.get(@term_key, nil) == nil, do: do_load(false)
    {:noreply, state}
  end

  def handle_info(_message, state), do: {:noreply, state}

  # --- loading -------------------------------------------------------------

  defp do_load(force) do
    dir = Config.data_dir()
    fingerprint = fingerprint(dir)

    graph =
      with false <- force,
           {:ok, cached} <- read_cache(fingerprint) do
        cached
      else
        _ ->
          graph = Graph.build(dir)
          write_cache(fingerprint, graph)
          graph
      end

    :persistent_term.put(@term_key, graph)
    graph
  end

  defp fingerprint(dir) do
    files =
      dir
      |> Path.join("*.csv")
      |> Path.wildcard()
      |> Enum.sort()
      |> Enum.map(fn path ->
        stat = File.stat!(path)
        {Path.basename(path), stat.size, stat.mtime}
      end)

    {@cache_version, dir, files}
  end

  defp read_cache(fingerprint) do
    with path when is_binary(path) <- Config.cache_file(),
         {:ok, binary} <- File.read(path),
         {^fingerprint, %Graph{} = graph} <- safe_binary_to_term(binary) do
      {:ok, graph}
    else
      _ -> :error
    end
  end

  # `:safe` refuses to invent atoms, which is what we want from a file on
  # disk — but it also means the atoms in the cached graph have to exist
  # already, so the modules that define them are loaded first.
  @atom_holders [
    BrazilianSoccer.Data.Graph,
    BrazilianSoccer.Data.Loader,
    BrazilianSoccer.Model.Competition,
    BrazilianSoccer.Model.Match,
    BrazilianSoccer.Model.Player,
    BrazilianSoccer.Model.Team
  ]

  defp safe_binary_to_term(binary) do
    Enum.each(@atom_holders, &Code.ensure_loaded/1)
    :erlang.binary_to_term(binary, [:safe])
  rescue
    _ -> :invalid
  end

  defp write_cache(fingerprint, graph) do
    case Config.cache_file() do
      nil ->
        :ok

      path ->
        File.mkdir_p!(Path.dirname(path))
        tmp = path <> ".tmp"

        case File.write(tmp, :erlang.term_to_binary({fingerprint, graph}, compressed: 6)) do
          :ok ->
            File.rename(tmp, path)

          {:error, reason} ->
            Logger.warning("could not write graph cache: #{inspect(reason)}")
            :ok
        end
    end
  end
end
