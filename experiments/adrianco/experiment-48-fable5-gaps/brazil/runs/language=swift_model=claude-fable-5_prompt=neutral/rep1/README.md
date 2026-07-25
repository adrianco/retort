# Brazilian Soccer MCP Server (Swift)

An MCP (Model Context Protocol) server that answers natural language questions
about Brazilian soccer — matches, teams, players, competitions and statistics —
from six Kaggle datasets. Implemented in Swift with no external dependencies,
per the specification in `TASK.md` / `brazilian-soccer-mcp-guide.md`.

## What was built

- **`Sources/BrazilianSoccerKit/`** — the library:
  - `CSVParser.swift` — byte-level RFC 4180 CSV parser (quoted fields, escaped
    quotes, CR/LF, UTF-8 BOM); parses the ~11 MB of data in well under a second.
  - `TeamNames.swift` — team name normalization. "Palmeiras-SP", "Palmeiras",
    "América - MG", "America MG", "Athletico Paranaense" and "Atlético-PR" all
    collapse to canonical keys (accent-folded, state suffix stripped, alias
    table applied). Ambiguous bases (Atlético, América, Botafogo, Guarani...)
    keep a state qualifier so Atlético-MG/GO/PR stay distinct.
  - `Models.swift` — `Match`, `Player`, `Competition` and date utilities that
    normalize the three date formats (`2012-05-19 18:30:00`, `29/03/2003`,
    `2023-09-24`) to ISO.
  - `DataStore.swift` — loads all six CSVs into one de-duplicated store. The
    Brasileirão appears in three overlapping sources; matches are merged by
    (competition, home, away) with ±1-day tolerance (BR-Football records UTC
    dates that can differ by a day). 2019 Série A collapses from 3×380 source
    rows to exactly 380 unique matches.
  - `QueryEngine.swift` — match search, head-to-head, team records with
    home/away splits, standings calculated from results (points/wins/GD/GF
    tiebreaks), league statistics, player search.
  - `MCPTools.swift` — the 8 MCP tools and answer formatting.
  - `MCPServer.swift` — JSON-RPC 2.0 over the MCP stdio transport (one JSON
    message per line): `initialize`, `ping`, `tools/list`, `tools/call`.
- **`Sources/BrazilianSoccerMCP/main.swift`** — the executable: loads data,
  then serves stdin/stdout; diagnostics go to stderr.
- **`Tests/BrazilianSoccerKitTests/`** — 49 BDD (Given/When/Then) tests, all
  passing; see below.

## Tools exposed

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team/opponent/competition/season/date range/stage, plus head-to-head summary |
| `head_to_head` | Full record between two teams across all competitions |
| `team_stats` | W/D/L, goals, win rate; filter by season, competition, home/away |
| `competition_standings` | Season table calculated from results (e.g. 2019: Flamengo champion, 90 pts) |
| `league_stats` | Matches, average goals, home/draw/away rates, biggest wins |
| `search_players` | FIFA players by name/nationality/club/position/min rating |
| `top_players` | Highest-rated players with optional filters |
| `data_summary` | Loaded files, counts, competition/season coverage |

Data coverage after de-duplication: ~16,850 unique matches (Série A 2003–2023,
Série B/C 2014–2023, Copa do Brasil, Copa Libertadores) and 18,207 FIFA
players. Note: the FIFA dataset (FIFA 19) does not license every Brazilian
club — Grêmio, Santos, Cruzeiro, Fluminense etc. are present; Flamengo,
Palmeiras and Corinthians are not.

## Build, test, run

```sh
swift build                      # library + executable
swift test                       # 49 BDD tests (needs full Xcode for XCTest)
swift build -c release
./.build/release/brazilian-soccer-mcp            # data dir defaults to ./data/kaggle
./.build/release/brazilian-soccer-mcp --data /path/to/data/kaggle
```

If `xcode-select` points at the Command Line Tools (no XCTest), run tests with
`DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift test`.

Example MCP client configuration (e.g. Claude Desktop / Claude Code):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/.build/release/brazilian-soccer-mcp",
      "args": ["--data", "/path/to/repo/data/kaggle"]
    }
  }
}
```

Startup (all six CSVs parsed, normalized and de-duplicated) takes ~0.3 s in a
release build; every query answers in milliseconds, well inside the < 2 s / < 5 s
targets.

## Testing

BDD-structured XCTest suites, one Given/When/Then scenario per test:

- `DataLoadingTests` — all six files load, de-duplication yields exactly 380
  matches for 2019 Série A, UTF-8 accents preserved, mixed date formats
  normalized, extended stats merged in.
- `TeamNameTests` — spelling/suffix/accent/alias variants collapse; ambiguous
  clubs stay distinct; registry query resolution.
- `MatchQueryTests` — Fla-Flu derby search, season/competition/date filters,
  Libertadores finals, head-to-head consistency, unknown-team errors.
- `TeamStatsAndStandingsTests` — Corinthians' 2022 home record (19 matches),
  home+away=total invariants, 2019 standings (Flamengo 90 pts, 28W 6D 4L,
  20 teams × 38 games), 2003 historical table consistency.
- `StatisticsTests` — average goals plausibility, home advantage, biggest-win
  ordering, season comparisons.
- `PlayerQueryTests` — name/nationality/club/position filters, accent-free
  club queries, cross-file join of player and match data via canonical keys.
- `MCPServerTests` — initialize handshake, tools/list schemas, tools/call
  results, in-band tool errors, JSON-RPC error codes (-32700/-32601/-32602).
- `SampleQuestionsAndPerformanceTests` — 23 sample questions from the spec all
  answered; simple lookups < 2 s and aggregates < 5 s.

## Specification

`TASK.md` (same content as `brazilian-soccer-mcp-guide.md`)

## Data Sources

Kaggle data can't be downloaded without an account so these (freely available
with attribution) data sets have been downloaded for use here:

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
