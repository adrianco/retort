# Brazilian Soccer MCP with spec and basic data sets

## Running the server

Build the dependency-free C MCP server with `make`, then run
`./brazilian_soccer_mcp`. It uses JSON-RPC messages, one JSON object per line,
on standard input/output and loads `data/kaggle/` by default (an alternative
data directory may be supplied as the first argument).

It implements the MCP `initialize`, `tools/list`, and `tools/call` methods.
The available tools are `search_matches`, `team_statistics`, `head_to_head`,
`search_players`, `competition_standings`, and `competition_statistics`.
Filters use human-readable names; team comparisons are case-, punctuation-,
accent-, and state-suffix tolerant. Run `make test` for the BDD-style smoke
scenarios.

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
