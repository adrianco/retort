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

## Implementation (TypeScript MCP server)

```
npm install
npm run build
npm test          # 32 tests: normalization, all 6 files, 24 sample questions, MCP round-trip
npm start         # stdio MCP server
```

Claude Desktop / Claude Code config:
```json
{ "mcpServers": { "brazilian-soccer": { "command": "node", "args": ["/abs/path/dist/src/server.js"] } } }
```
Set `SOCCER_DATA_DIR` to override the data location (default `data/kaggle`).

### Layout
- `src/csv.ts` – RFC-4180 CSV parser (quotes, BOM)
- `src/normalize.ts` – team-name keys (accents, state suffixes "-SP"/" - MG"/" RJ", aliases like "Athletico Paranaense", "Vasco da Gama"; keeps the state for ambiguous names like Botafogo-RJ/SP), date parsing (ISO, DD/MM/YYYY, with time)
- `src/data.ts` – loads all 6 CSVs in memory (~0.4 s), deduplicates overlapping matches across files (merging corner/shot stats from BR-Football), labels Copa do Brasil finals
- `src/queries.ts` – query/aggregation functions returning formatted text
- `src/server.ts` – MCP tools

### Tools
`search_matches`, `head_to_head`, `team_record`, `standings`, `season_champion`, `relegated_teams`,
`competition_stats`, `compare_seasons`, `biggest_wins`, `rank_teams`, `team_competitions`, `derbies`,
`search_players`, `player_details`, `brazilian_clubs_players`, `team_profile`, `dataset_info`.

### Data caveats
- Brasileirão standings use one source per season (Brasileirao_Matches 2012–2022, novo_campeonato 2003–2011, BR-Football 2023) to avoid double counting. The 2023 BR-Football data is incomplete, so the table is flagged as such.
- The FIFA 19 dataset uses licensed-out placeholder names for many Brazilian club players and does not include Flamengo/São Paulo; name lookups fall back to closest matches.
