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

## Implementation (Objective-C)

An MCP server implemented in Objective-C (Foundation, no third-party
dependencies) that loads all six CSVs into memory at startup and answers
JSON-RPC 2.0 requests over stdio (newline-delimited JSON, per the MCP stdio
transport).

### Build and test

```sh
make          # builds ./bss-mcp-server and ./bss-tests
make test     # runs the BDD-style test suite against data/kaggle
```

Requires the Xcode Command Line Tools (clang + Foundation). Data loads in
about a second; queries answer in milliseconds.

### Running the server

```sh
./bss-mcp-server [path/to/data/kaggle]
```

The data directory can also be set with `BSS_DATA_DIR`; it defaults to
`data/kaggle` relative to the working directory. Example client entry
(Claude Code):

```sh
claude mcp add brazilian-soccer -- /path/to/bss-mcp-server /path/to/data/kaggle
```

### Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team/opponent/competition/season/date range, plus head-to-head summary |
| `get_head_to_head` | Full head-to-head record between two teams with recent meetings |
| `get_team_stats` | W/D/L, goals, win rate for a team; season/competition/venue filters |
| `get_standings` | League table computed from results (Série A 2003–2023, also Série B/C) |
| `search_players` | FIFA players by name/nationality/club/position/min rating |
| `get_player` | Detailed FIFA profile for one player |
| `get_analytics` | avg goals, biggest wins, best home/away records, top scoring teams |
| `get_data_summary` | Datasets loaded, match/player counts, season coverage |

### Source layout

| File | Contents |
|------|----------|
| `BSCSV.h/.m` | RFC-4180-style CSV parser (quotes, embedded newlines, BOM, CRLF) |
| `BSModels.h/.m` | `BSMatch`/`BSPlayer` models and team-name normalization |
| `BSDataStore.h/.m` | CSV loading, cross-file deduplication, all query logic |
| `BSTools.h/.m` | MCP tool definitions (JSON Schema) and text formatting |
| `BSMCPServer.h/.m` | JSON-RPC 2.0 / MCP protocol handling and stdio loop |
| `main.m` | Entry point; resolves the data directory |
| `tests_main.m` | Given/When/Then test suite incl. end-to-end stdio test |

### Data-handling notes

- **Team names** are normalized (lowercase, accents stripped, `-SP` / ` - MG` /
  trailing-UF and `(URU)` markers removed, club-token cleanup, alias table) so
  "Palmeiras-SP", "Palmeiras" and "São Paulo"/"Sao Paulo" match. Clubs sharing
  a name are kept apart by state (Atlético-MG ≠ Atlético-GO).
- **Deduplication**: the five match files overlap heavily (e.g. Série A
  2014–2019 appears in three files). Fixtures are merged on
  date(±1 day)+teams; extended stats (corners/shots) and late-arriving scores
  ("NA" fixtures in `Brasileirao_Matches.csv` 2022) are merged into the kept
  row. ~7,000 duplicates collapse into 16,857 unique matches.
- **Known data quirks handled**: three date formats, float goal values,
  `nan` fields, unreliable UF columns in `novo_campeonato_brasileiro.csv`
  (Vitória listed as ES at home / BA away), inconsistent casing
  ("ABC - RN" vs "Abc - RN"), and the FIFA 19 dataset's missing Brazilian
  club licenses (no Flamengo/Palmeiras/Corinthians/São Paulo squads).
