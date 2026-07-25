defmodule BrazilianSoccerMcp do
  @moduledoc """
  Brazilian Soccer MCP Server.

  An MCP (Model Context Protocol) server exposing a queryable knowledge base
  of Brazilian soccer built from six Kaggle CSV datasets: Brasileirão Série A
  matches (2012-2023 and 2003-2019 historical), Copa do Brasil, Copa
  Libertadores, extended match statistics (corners/shots/attacks), and FIFA
  player data.

  Layers:

    * `BrazilianSoccerMcp.CSV`       - dependency-free RFC 4180 CSV parser
    * `BrazilianSoccerMcp.TeamNames` - team name normalization across datasets
    * `BrazilianSoccerMcp.DataStore` - loads, deduplicates, and indexes the data
    * `BrazilianSoccerMcp.Queries`   - match/team/player/statistics queries
    * `BrazilianSoccerMcp.Format`    - human-readable answer formatting
    * `BrazilianSoccerMcp.Tools`     - MCP tool schemas and dispatch
    * `BrazilianSoccerMcp.Server`    - JSON-RPC 2.0 protocol handling
    * `BrazilianSoccerMcp.Stdio`     - stdio transport loop

  Start with `mix mcp.server` or build an escript with `mix escript.build`.
  """
end
