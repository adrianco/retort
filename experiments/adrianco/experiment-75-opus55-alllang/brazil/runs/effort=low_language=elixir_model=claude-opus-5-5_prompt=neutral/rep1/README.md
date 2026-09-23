# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv

## Elixir MCP server

No external dependencies (uses Elixir ≥ 1.18's built-in `JSON`).

```sh
mix test          # BDD-style feature tests over the real data
./run_mcp.sh      # MCP server on stdio (JSON-RPC 2.0, protocol 2024-11-05)
```

Claude Code: `claude mcp add brazilian-soccer -- /path/to/run_mcp.sh`

Tools: `search_matches`, `head_to_head`, `team_stats`, `team_competitions`, `standings`,
`cup_finals`, `competition_stats`, `biggest_wins`, `best_records`, `top_scoring_teams`,
`derbies`, `compare_seasons`, `search_players`, `players_by_club`, `club_profile`.

Code: `lib/br_soccer/` — `csv.ex` (parser), `team.ex` (name normalization, rivalries),
`data.ex` (loading + cross-file dedup), `query.ex` (queries/aggregates), `tools.ex` (MCP tools),
`mcp_server.ex` (stdio JSON-RPC).
