defmodule BrazilianSoccer do
  @moduledoc """
  Brazilian Soccer knowledge-graph MCP server.

  This top-level module is a convenience entry point. The pieces are:

    * `BrazilianSoccer.DataLoader` — parse the Kaggle CSV files into a `Dataset`
    * `BrazilianSoccer.Dataset` — the in-memory matches + players collection
    * `BrazilianSoccer.Queries.*` — match, team, player, competition and
      statistical queries
    * `BrazilianSoccer.MCP.*` — the Model Context Protocol server (tools,
      JSON-RPC handling and the stdio transport)

  ## Quick start

      iex> ds = BrazilianSoccer.load()
      iex> BrazilianSoccer.Queries.Competitions.champion(ds, "Brasileirão Série A", 2019).team
      "Flamengo"
  """

  alias BrazilianSoccer.DataLoader

  @doc "Load the bundled datasets into a `BrazilianSoccer.Dataset`."
  @spec load(String.t()) :: BrazilianSoccer.Dataset.t()
  def load(dir \\ DataLoader.default_dir()), do: DataLoader.load!(dir)
end
