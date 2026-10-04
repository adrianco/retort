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

## Brazilian Soccer MCP Server (TypeScript)

Build & run:

```bash
npm install
npm run build
npm test
node dist/server.js        # MCP server over stdio
```

Claude Desktop / Claude Code config:

```json
{ "mcpServers": { "brazilian-soccer": { "command": "node", "args": ["/abs/path/dist/server.js"] } } }
```

Set `SOCCER_DATA_DIR` to override the default `data/kaggle` location.

### Tools
`search_matches`, `last_match`, `head_to_head`, `team_record`, `standings`, `top_scoring_teams`,
`biggest_wins`, `match_statistics`, `best_records`, `team_competitions`, `derbies`, `compare_seasons`,
`search_players`, `player_details`, `players_by_club`, `team_profile` (cross-file), `list_teams`, `dataset_info`.

### Design notes
- `src/data.ts` – CSV parsing (quotes, BOM, UTF-8), date normalization (ISO / DD/MM/YYYY / with time), team-name normalization (state suffixes, accents, full club names, aliases; ambiguous names such as Atlético keep their state).
- `src/queries.ts` – filtering, cross-file de-duplication (same date + teams), standings, records, head-to-head, stats.
- `src/tools.ts` – MCP tool definitions (zod schemas) and text formatting; `src/server.ts` – stdio server.
- League tables use one primary file per season (`Brasileirao_Matches.csv` for 2012–2022, the historical file for 2003–2011, the extended dataset for 2023) and fill fixtures with missing scores (`NA`) from the other files.
- Data limitations: the FIFA 19 data has no Flamengo/Palmeiras/São Paulo squads (it does include Grêmio, Internacional, Cruzeiro, Atlético Mineiro, etc.), and the 2023 data stops before the season ends.
