# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Implementation

A TypeScript MCP (Model Context Protocol) server that loads the six Kaggle CSV
datasets in `data/kaggle/` and exposes them as a set of tools an LLM can call.

### Quick start
```
npm install
npm run build
npm start          # runs the MCP server over stdio
npm test           # runs the BDD-style vitest suite
```

### Exposed tools
- `find_matches` — filter by team / opponent / competition / season / date range
- `team_record` — win/draw/loss record with venue + season filters
- `head_to_head` — head-to-head between any two clubs
- `competition_standings` — final table for a season, calculated from results
- `find_players` — search FIFA player data by name, nationality, club, position
- `top_scoring_teams` — goals scored rankings
- `biggest_wins` — largest margin matches
- `aggregate_stats` — averages and home/away/draw rates
- `brazilian_players_by_club` — Brazilian players grouped by club
- `competitions_for_team` — which competitions a team appears in

### Layout
- `src/loader.ts` — CSV parsing, team-name normalization, cross-source dedup
- `src/normalize.ts` — team name + date + season normalization
- `src/queries.ts` — pure query functions
- `src/format.ts` — render results as human-readable text
- `src/server.ts` — `McpServer` wiring + stdio transport
- `tests/` — BDD-style vitest scenarios

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
