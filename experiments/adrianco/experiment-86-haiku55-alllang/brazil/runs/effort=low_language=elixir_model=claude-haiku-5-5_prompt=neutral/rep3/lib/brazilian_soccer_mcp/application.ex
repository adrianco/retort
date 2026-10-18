defmodule BrazilianSoccerMcp.Application do
  @moduledoc false

  use Application

  @default_data_dir "data/kaggle"

  @impl true
  def start(_type, _args) do
    children = [{BrazilianSoccerMcp.Store, data_dir: data_dir()}]
    Supervisor.start_link(children, strategy: :one_for_one, name: BrazilianSoccerMcp.Supervisor)
  end

  @doc "Directory holding the CSV files. Override with `SOCCER_DATA_DIR`."
  def data_dir do
    System.get_env("SOCCER_DATA_DIR") ||
      Application.get_env(:brazilian_soccer_mcp, :data_dir, @default_data_dir)
  end
end
