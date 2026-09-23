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

## Implementation

- `soccer_data.py` — loads all 6 CSVs (UTF-8), normalizes team names/dates, dedupes overlapping datasets, and implements match/team/player/competition/statistics queries.
- `mcp_server.py` — dependency-free MCP stdio server (JSON-RPC 2.0) exposing 12 tools (`search_matches`, `head_to_head`, `team_stats`, `league_standings`, `team_rankings`, `competition_stats`, `biggest_wins`, `derbies`, `team_competitions`, `search_players`, `brazilian_club_players`, `club_profile`).
- Run: `python3 mcp_server.py` (e.g. `claude mcp add brazilian-soccer -- python3 /path/to/mcp_server.py`).
- Tests: `python3 -m pytest tests`
