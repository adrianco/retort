defmodule BrazilianSoccer.Config do
  @moduledoc """
  Where the CSVs live and where the parsed graph is cached.

  Resolution order for both settings: environment variable, application
  config, then a path relative to the project root that was baked in at
  compile time (so `mix test` and the escript both work out of the box).
  """

  @project_root Path.expand("../..", __DIR__)

  @doc "Directory holding the Kaggle CSV files."
  @spec data_dir() :: Path.t()
  def data_dir do
    System.get_env("BRAZILIAN_SOCCER_DATA_DIR") ||
      Application.get_env(:brazilian_soccer, :data_dir) ||
      Path.join([@project_root, "data", "kaggle"])
  end

  @doc "File used to memoise the parsed graph between runs (`nil` disables caching)."
  @spec cache_file() :: Path.t() | nil
  def cache_file do
    case System.get_env("BRAZILIAN_SOCCER_CACHE") do
      "false" ->
        nil

      nil ->
        Application.get_env(:brazilian_soccer, :cache_file, default_cache_file())

      path ->
        path
    end
  end

  @doc "Project root directory."
  def project_root, do: @project_root

  defp default_cache_file, do: Path.join([@project_root, "_build", "brazilian_soccer_graph.cache"])
end
