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

## Clojure MCP server

- Run (stdio JSON-RPC MCP server): `clojure -M:run`
- Tests (BDD-style scenarios): `clojure -M:test`
- Code: `src/soccer/data.clj` (CSV loading, team-name/date normalization), `src/soccer/query.clj` (queries & stats), `src/soccer/server.clj` (MCP tools)

Tools: search_matches, head_to_head, team_stats, standings, top_scoring_teams, competition_stats, best_records, team_competitions, cup_finals, derbies, search_players, brazilian_players_by_club, player_profile.
