# Brazilian Soccer MCP Server

A TypeScript [Model Context Protocol](https://modelcontextprotocol.io) server that answers natural-language-friendly questions about Brazilian soccer, using the six Kaggle CSV files in `data/kaggle/`. Spec: `TASK.md` (also `brazilian-soccer-mcp-guide.md`).

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

## Setup

```bash
npm install
npm run build
npm start          # stdio MCP server
npm test           # vitest: unit, BDD-style and end-to-end MCP tests
```

Set `BRAZIL_SOCCER_DATA_DIR` to load CSVs from another directory. Example client config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/dist/index.js"]
    }
  }
}
```

## Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, competition, season/date range, or finals only |
| `team_record` | Wins/draws/losses, goals, win rate for a team (optionally by season, competition, venue) |
| `head_to_head` | All meetings between two teams with win/draw/goal totals |
| `standings` | Points table for a season, calculated from results (3/1/0, ties by wins, GD, GF) |
| `rank_teams` | Rank by win rate, wins, goals for, goal difference, or points per match |
| `league_stats` | Average goals per match, home/draw/away rates |
| `biggest_wins` | Largest winning margins |
| `search_players` | FIFA players by name, nationality, club, position, minimum overall |
| `team_profile` | Match record plus squad members from the FIFA file |
| `club_summary` | Player count and average overall per club (optionally by nationality) |
| `dataset_info` | Rows read and matches loaded per file |

## Design

- `src/csv.ts` — RFC 4180 reader (quotes, escaped quotes, CRLF, BOM); no CSV dependency.
- `src/normalize.ts` — team names (state suffixes, parentheticals, accents, "FC"/"EC", known renames such as Atlético-PR → Athletico-PR), competition names, dates (ISO, ISO with time, DD/MM/YYYY), goals (`2.0`, `NA`).
- `src/loader.ts` — maps the six files to one `Match` shape and loads the FIFA file to `Player`. Then:
  1. **Source priority per competition and season**: Brasileirão_Matches > novo_campeonato > BR-Football; Cup and Libertadores each have one source.
  2. **Dedupe** fixtures that appear twice (same teams, same score, dates within one day).
  3. **State inference**: a bare team name seen with only one state in the dataset takes that state so clubs group together.
- `src/queries.ts` — pure query functions (no I/O), tested directly.
- `src/tools.ts` — MCP tool registration with zod input schemas; `src/format.ts` — answer text.
- `src/index.ts` — stdio entry point. The dataset loads once at startup (~0.3 s).

Unplayed fixtures (`NA` scores) are skipped, so standings and records count only played games.

## Known data limitations

- **FIFA data is FIFA 19 and has no Flamengo, Palmeiras, Corinthians, etc.** Player queries work for clubs that appear in it (e.g. Santos, Manchester City); a club missing from the file returns "No players found."
- **The 2022 Brasileirão file is incomplete**: 81 of its 2022 fixtures have no score yet, so 2022 standings show about 30 played games per club.
- **2023 comes only from BR-Football**, which is missing some fixtures; a few clubs show 37 games.
- **Bare "Atletico"** is ambiguous (MG, GO). Queries should include the state (`Atletico-MG`) to be exact. Only Atlético-PR is mapped automatically (to Athletico).
- **Copa do Brasil "finals"** are the highest round number in each season (the file has no stage label). Libertadores finals use the `final` stage.
- **Team name variants** in the cup and Libertadores files (e.g. "Nacional (URU)") match by the base name only.

## Tests

`test/` holds vitest suites organised as Gherkin-style `Feature` / `Scenario` blocks with Given/When/Then comments. `features/brazilian-soccer.feature` lists the scenarios in plain Gherkin.

- `csv.test.ts`, `normalize.test.ts` — parsing and name rules
- `queries.test.ts` — query logic on a small in-memory dataset with known answers
- `loader.test.ts` — the real Kaggle files: all six load, 2019 standings match the published table, dedupe holds
- `tools.test.ts` — the MCP tools over the real MCP protocol (in-memory transport), using the spec's example questions
