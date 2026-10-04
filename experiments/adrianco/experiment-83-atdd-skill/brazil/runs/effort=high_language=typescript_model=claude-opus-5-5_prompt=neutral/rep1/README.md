# Brazilian Soccer MCP Server

A TypeScript [Model Context Protocol](https://modelcontextprotocol.io) server that lets an LLM answer
natural-language questions about Brazilian soccer: matches, teams, players, competitions and statistics.
It implements the specification in `TASK.md` / `brazilian-soccer-mcp-guide.md` using the six Kaggle
datasets in `data/kaggle/`.

## Quick start

```bash
npm install
npm run build
npm test            # 83 tests (unit, 27 sample questions, MCP protocol, performance)
npm start           # MCP server on stdio
```

Register it with an MCP client (e.g. Claude Desktop / Claude Code):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/this/repo/dist/index.js"]
    }
  }
}
```

The data directory is found automatically (`./data/kaggle` relative to the working directory or the
package). Set `BRAZIL_SOCCER_DATA_DIR` to use a different directory.

## Tools

| Tool | What it answers |
|------|-----------------|
| `search_matches` | Matches by team, opponent, home/away, competition, season, date range, cup stage, round. "Show me all Flamengo vs Fluminense matches", "When did Flamengo last play Corinthians?" (`limit: 1`) |
| `head_to_head` | W/D/L between two teams, goals, per-competition split, derby name, recent meetings |
| `team_record` | Record for a team (optionally home/away, season, competition): "Corinthians' home record in 2022" |
| `team_profile` | Cross-file overview: competitions & seasons played, record, derbies, linked FIFA squad |
| `standings` | League table computed from results (Série A 2003-2023, B/C 2014-2023): champion, relegation |
| `cup_bracket` | Knockout ties for Libertadores / Copa do Brasil with aggregates and who advanced |
| `cup_finals` | Every final in the data with winner |
| `match_statistics` | Goals per match, home/draw/away rates, common scorelines, shots/corners averages |
| `biggest_wins` | Largest victories (by competition, season or team) |
| `team_rankings` | Rank teams by points, win rate, home/away win rate, goals for/against, clean sheets... |
| `compare_seasons` | Side-by-side season stats with champion and top-scoring team |
| `derbies` | Traditional rivalry matches (Fla-Flu, Grenal, Derby Paulista, Clássico Mineiro, Ba-Vi, ...) |
| `search_players` | FIFA players by name, nationality, club, position (code or group: forward/defender...), rating, age |
| `get_player` | Full player profile; suggests similar names if not found |
| `club_player_summary` | Players per club (e.g. Brazilians at Brazilian clubs) or per nationality |
| `find_team` | Resolve/disambiguate a team name and show its spellings |
| `dataset_info` | Files loaded, row counts, coverage |

Query errors (unknown team, season out of range, standings for a knockout cup) come back as MCP tool
errors with an explanatory message so the LLM can recover.

## Design

```
src/
  csv.ts        RFC-4180 CSV parser (quotes, CRLF, UTF-8 BOM)
  normalize.ts  accent folding, number parsing, multi-format date parsing
  teams.ts      team-name parsing, canonical club registry, derbies, TeamRegistry
  data.ts       loads the 6 CSVs, merges duplicate matches, links FIFA clubs to teams
  query.ts      SoccerQueries: search, records, H2H, standings, brackets, rankings, players
  format.ts     text rendering in the answer formats of the spec
  tools.ts      MCP tool definitions (zod schemas + handlers)
  server.ts     McpServer wiring and error handling
  index.ts      stdio entry point
tests/          vitest suites
```

All data is loaded into memory at startup (~300 ms) and indexed by team; every query runs in a few
milliseconds, far inside the 2 s / 5 s targets.

### Data handling

* **Team names.** Each raw name is parsed into base name + Brazilian state (`-SP`, ` - SP`, ` SP`,
  `(PI)`) or foreign country qualifier (`-URU`, `(PAR)`); accents, dots (`C.R.B.`) and club-type words
  (`EC`, `FC`, `Sport Club`...) are normalised. A registry of ~50 major clubs with their home states
  resolves aliases ("Atlético-MG" = "Atlético Mineiro", "Sport Club do Recife" = "Sport Recife",
  "Bragantino" = "Red Bull Bragantino") and keeps namesakes from other states apart ("Flamengo - PI",
  "Santos AP", "Botafogo PB"). User input goes through the same resolver plus fuzzy matching.
* **Duplicate matches.** Série A 2012-2019 appears in three files and Copa do Brasil 2014-2021 in two.
  Matches are merged (league: competition+season+home+away; cups: home+away within 3 days) so each
  fixture is counted once, and the merged record keeps the round (Brasileirao_Matches), arena
  (novo_campeonato_brasileiro) and shots/corners (BR-Football) plus the list of source files.
* **Seasons.** BR-Football has no season column; league matches played Jan-Mar are assigned to the
  previous season (the COVID-delayed 2020 season ended in Feb 2021).
* **Dates.** ISO, ISO with time and Brazilian `DD/MM/YYYY` are all normalised to `YYYY-MM-DD`.
* **Data quality.** Rows without a score (`NA`, unplayed 2022 Libertadores final) are skipped and
  reported by `dataset_info`; the unreliable state columns of the 2003-2019 file (e.g. Vitória "ES")
  are ignored; a few mislabelled league rows in BR-Football are dropped.
* **Cup stages.** Copa do Brasil rounds are numeric; the last round with a single tie is labelled
  `final` (or, for seasons only in BR-Football, the last two-legged tie of the season). Bracket
  winners are inferred from aggregate score or, when level, from which team appears in the next stage.
* **Players.** FIFA 19 data. A club is treated as Brazilian when ≥75 % of its squad is Brazilian
  (15 Série A clubs); these are linked to match-data teams for cross-file queries. Note that FIFA 19
  did not license Flamengo, Palmeiras, Corinthians, São Paulo or Vasco, and players at Brazilian clubs
  have generated names — the tools say so instead of returning nothing silently.

### Verified against real results

Computed standings reproduce the actual tables, e.g. 2019 Série A: Flamengo 90 pts (28W 6D 4L),
Santos 74, Palmeiras 74; 2020 relegations: Vasco, Goiás, Coritiba, Botafogo; 2018 champion
Palmeiras (80 pts). Copa do Brasil and Libertadores finals match the real winners (2018 Libertadores:
River Plate 5-3 Boca Juniors on aggregate). 2023 Série A is missing 3 matches in the source file and
the standings tool flags it as incomplete.

## Tests

`npm test` runs:

* `csv`, `normalize`, `teams`: parser, date formats, accents, team-name variants and disambiguation
* `data`: all 6 files load with expected row counts, duplicate merging, season fix-up, UTF-8, FIFA linkage
* `sample-questions`: 27 questions from the spec (match, team, player, competition, statistics,
  cross-file) checked against known facts
* `mcp`: real MCP client ↔ server over an in-memory transport: tool listing, calls, error handling,
  every tool exercised
* `performance`: load and query latency budgets

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
