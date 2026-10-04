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

## MCP server (TypeScript)

    npm install && npm run build
    npm start            # MCP server on stdio (dist/server.js)
    npm test             # builds, then runs acceptance tests

Tools: search_matches, last_meeting, team_record, head_to_head, team_competitions, team_profile,
search_players, players_by_club, standings, libertadores_bracket, stats_overview, biggest_wins,
best_records, compare_seasons.

Acceptance tests follow the four-layer model: specs (`acceptance/*.spec.ts`) → DSL (`acceptance/dsl`)
→ MCP protocol driver (`acceptance/drivers`, talks to the real server over stdio) → system (`src`).
