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

A TypeScript [Model Context Protocol](https://modelcontextprotocol.io) server over the bundled CSVs, served over stdio.

```bash
npm install
npm run build
npm start            # or: node dist/index.js
npm test
```

Set `BRAZIL_SOCCER_DATA_DIR` to read CSVs from a directory other than `data/kaggle/`.

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season or date range |
| `team_record` | W/D/L, goals and win rate for a team, optionally by venue, season or competition |
| `head_to_head` | All meetings between two teams, from the first team's perspective |
| `standings` | League table for a season, calculated from results (3 pts win, 1 pt draw) |
| `search_players` | FIFA players by name, nationality, club, position or minimum rating |
| `club_squad_summary` | Players and average rating per club, e.g. Brazilian players by club |
| `match_statistics` | Average goals, home/draw/away rates and biggest wins |

### Design notes

- **Loading** (`src/loader.ts`): all six files are parsed on first use (about 0.3 s) into one list of matches. A fixture listed in more than one file is kept once. Files disagree on team spelling (`Sao Paulo`, `São Paulo-SP`, `Athletico-PR` vs `Athletico Paranaense`) and occasionally on the date by one day, so a fixture is a duplicate when the date is within a day, the score matches, and one club's leading name word matches.
- **Names** (`src/normalize.ts`): team names are folded to lowercase without accents, with state suffixes and parenthetical notes handled. A query matches whole words, so `Flamengo` matches `Flamengo-RJ` and `Corinthians` matches `Sport Club Corinthians Paulista`.
- **Dates**: `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS` and `DD/MM/YYYY` are all accepted.
- **Competitions**: Brasileirão Série A/B/C, Copa do Brasil and Copa Libertadores. A competition filter matches whole words, so `Brasileirão` covers all Brasileirão series.

### Tests

`tests/` uses Vitest with Given/When/Then-named cases. Unit tests use small fixtures with hand-checked expectations. Loader and server tests run against the real CSVs, including an in-memory MCP client that calls every tool.

### Known limits

- Standings are only as complete as the source data, and the datasets overlap and disagree in places. Some seasons have more or fewer matches than the official calendar.
- The data has no relegation or top-scorer fields. Relegation can be inferred from final standings, and goals-for is shown per team in `standings`.
- Player data is the FIFA snapshot, so ratings and clubs are as of that snapshot.
