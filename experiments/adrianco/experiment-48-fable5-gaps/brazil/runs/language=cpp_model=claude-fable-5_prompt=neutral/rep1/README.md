# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, written in C++17 with no external
dependencies, that answers natural-language-driven queries about Brazilian
soccer: Brasileirão Série A/B/C, Copa do Brasil and Copa Libertadores match
results (2003-2023) plus the FIFA player database.

## Specification
brazilian-soccer-mcp-guide.md (also TASK.md)

## Build and test

```sh
cmake -S . -B build
cmake --build build -j
ctest --test-dir build --output-on-failure
```

Requires CMake ≥ 3.16 and a C++17 compiler. Two test suites run:

- `test_unit` — BDD (Given/When/Then) scenarios covering CSV parsing, team
  name normalization, date handling, dataset loading/deduplication, and every
  query capability, verified against values computed independently from the
  raw CSVs (e.g. Flamengo's 90-point 2019 title, Corinthians' 2019 home
  record).
- `test_mcp_protocol` — spawns the real server binary and speaks
  newline-delimited JSON-RPC 2.0 over stdin/stdout: initialize handshake,
  tools/list, tools/call (including UTF-8 arguments), error codes for bad
  arguments, unknown tools/methods and malformed JSON, and the spec's
  response-time requirements (simple lookup < 2 s, aggregate < 5 s; in
  practice queries answer in microseconds from the in-memory store).

## Run

```sh
./build/soccer_mcp_server --data data/kaggle          # MCP server on stdio
./build/soccer_mcp_server --data data/kaggle --demo   # answer 26 sample questions
```

Claude Desktop / Claude Code configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/build/soccer_mcp_server",
      "args": ["--data", "/path/to/data/kaggle"]
    }
  }
}
```

## MCP tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season, date range, stage/round, venue; includes head-to-head summary |
| `get_team_stats` | W/D/L, goals, points, win rate; season/competition/venue filters; per-competition breakdown |
| `head_to_head` | Full head-to-head record between two teams plus recent meetings |
| `get_standings` | Season standings computed from results (3-1-0 points), champion and relegation zone |
| `search_players` | FIFA players by name, nationality, club, position, minimum rating |
| `get_player` | Detailed player profile (ratings, physique, key skills) |
| `get_competition_stats` | Match count, goals per match, home/draw/away rates, biggest win |
| `biggest_wins` | Largest margins of victory |
| `best_records` | Teams ranked by win rate (home/away/overall) |
| `list_teams` | Team name resolution helper with match counts |
| `list_competitions` | Competition coverage summary |

## Implementation notes

- `src/json.hpp` — minimal JSON parser/serializer (UTF-8, `\uXXXX` incl.
  surrogate pairs) for JSON-RPC messaging.
- `src/csv.cpp` — RFC 4180 CSV parsing: quoted fields, escaped quotes,
  embedded newlines, CRLF, UTF-8 BOM.
- `src/text.cpp` — normalization layer. Accent folding (São Paulo ≡ Sao
  Paulo), state/country suffix handling (`Palmeiras-SP`, `América - MG`,
  `Nacional (URU)`, `America MG` — two-letter suffixes must be real Brazilian
  state codes so "Fortaleza EC" is not misread), filler-word stripping
  ("Sport Club Corinthians Paulista" ≡ "Corinthians"), an alias table
  (Atlético Mineiro → Atlético-MG, Vasco ≡ Vasco da Gama, Red Bull
  Bragantino ≡ Bragantino, ...), and date normalization for ISO and
  DD/MM/YYYY formats.
- `src/db.cpp` — loads all six CSVs into one match store. Matches appearing
  in several files are deduplicated via three keys (competition+date+teams,
  competition+season+round+teams, and for league round-robins
  competition+season+teams), after resolving bare club names to their
  dominant state qualifier (so novo's "Flamengo" merges with
  "Flamengo-RJ" while lower-division namesakes like "Fluminense PI" and
  foreign clubs like "River Plate-URU" stay distinct). Extended statistics
  (corners, shots, attacks) and stadium names are merged into the canonical
  record. Data quirks handled: "NA" scores (the cancelled 2016 Chapecoense
  match, unfilled late-2022 fixtures backfilled from BR-Football), COVID
  season spillover (2020 Série A matches played in early 2021), and a
  mislabeled state-championship row.
- `src/tools.cpp` — the 11 MCP tools with JSON schemas and formatted,
  LLM-friendly text answers.
- `src/server.cpp` — MCP stdio transport: newline-delimited JSON-RPC 2.0,
  initialize/ping/tools handshake, JSON-RPC error codes (-32700/-32600/
  -32601/-32602/-32603), tool failures reported as `isError` content.

Dataset coverage after deduplication: ~17k unique matches (Série A
2003-2023, Série B/C 2014-2023, Copa do Brasil 2012-2023, Libertadores
2013-2023) and 18,207 FIFA players. Standings are derived purely from match
results; point deductions and tie-break rules beyond points/wins/goal
difference are not reflected.

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
