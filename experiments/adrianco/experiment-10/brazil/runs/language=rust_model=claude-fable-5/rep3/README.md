# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server written in **Rust** that answers natural
language questions about Brazilian soccer — matches, teams, players,
competitions and statistics — backed by six Kaggle CSV datasets
(~24,000 matches, 18,207 FIFA 19 players).

Implemented from the specification in `TASK.md` / `brazilian-soccer-mcp-guide.md`.

## What was done

- **Rust MCP server over stdio** (`src/server.rs`): newline-delimited
  JSON-RPC 2.0 implementing the MCP handshake (`initialize`,
  `notifications/initialized`, `ping`), `tools/list` and `tools/call`.
  Diagnostics go to stderr; stdout carries only protocol messages.
- **Data layer** (`src/data.rs`): loads all six CSVs into unified `Match` and
  `Player` records and handles the data-quality issues called out in the spec:
  - *Team-name normalization*: "Palmeiras-SP" ≡ "Palmeiras",
    "São Paulo" ≡ "Sao Paulo" (accent folding), "Athletico-PR" ≡ "Atlético-PR"
    (club rename), "América - MG" ≡ "América-MG". State suffixes are kept only
    for clubs that are ambiguous without one (Atlético-MG/GO/PR,
    América-MG/RN, Botafogo-RJ/SP/PB, ...). Long official names
    ("Sport Club Corinthians Paulista") match their short forms.
  - *Date formats*: `2012-05-19 18:30:00`, `2023-09-24` and `29/03/2003` are
    all parsed; `NA`/`-` values are handled gracefully.
  - *UTF-8*: accented Portuguese names are preserved in output.
- **Query engine** (`src/query.rs`): match search with filters, team
  statistics, head-to-head records, standings computed from results
  (3 pts/win), competition-wide statistics, and FIFA player search/profiles.
  - *Cross-dataset de-duplication*: the same fixture appears in up to three
    CSVs (e.g. 2015 Serie A is in Brasileirao_Matches, the historical file and
    the extended file). League/cup fixtures are de-duplicated by
    (competition, season, home, away) — robust even when sources disagree on
    the kick-off date by a day — and standings are computed from the single
    best source per season so nothing is double-counted.
  - The pandemic-delayed 2020 season's Jan/Feb-2021 rounds are attributed to
    season 2020.

## MCP tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season, date range, stage (incl. cup finals); adds a head-to-head summary when two teams are given |
| `get_team_stats` | W/D/L, goals for/against, win rate; filter by season, competition, venue (home/away); per-competition breakdown |
| `head_to_head` | Record between two teams plus most recent meetings |
| `get_standings` | League table for a season (champion + relegation zone marked); Serie A 2003–2023, Serie B 2014–2023 |
| `get_competition_stats` | Average goals/match, home-win/draw/away-win rates, biggest victories, highest-scoring games |
| `search_players` | FIFA 19 players by name, nationality, club, position (code or group: forward/midfielder/defender/goalkeeper), min rating |
| `get_player` | Detailed profile for one player by (partial) name |
| `get_data_summary` | Dataset inventory: files, competitions, season ranges, counts |

## Build, test, run

```sh
cargo build --release
cargo test                       # 23 BDD (Given/When/Then) tests
./target/release/brazilian-soccer-mcp [data-dir]   # default: ./data/kaggle
```

The data directory can also be set with the `BRAZILIAN_SOCCER_DATA`
environment variable.

### Claude Desktop / MCP client configuration

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/target/release/brazilian-soccer-mcp",
      "args": ["/path/to/data/kaggle"]
    }
  }
}
```

### Quick smoke test

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_standings","arguments":{"season":2019}}}' \
  | ./target/release/brazilian-soccer-mcp
```

returns the 2019 Brasileirão table with Flamengo as champion
(90 pts, 28W 6D 4L), matching the spec's expected output.

## Testing

`tests/bdd_tests.rs` contains 23 behavior-driven tests structured as
Given/When/Then scenarios covering the spec's success criteria: all six CSVs
load, match/team/player/competition queries, name normalization, date-format
handling, de-duplication of overlapping datasets, cross-file queries
(players + matches for one club), MCP protocol conformance (handshake, tool
listing, tool calls, error handling) and the < 2 s / < 5 s query performance
limits. `cargo clippy --all-targets` is warning-free.

## Known data limitations

- FIFA 19 lacks some unlicensed Brazilian clubs (no Flamengo/Palmeiras/São
  Paulo squads; Santos, Grêmio, Cruzeiro, Fluminense etc. are present) and
  some players (e.g. Gabriel Barbosa); missing lookups return a clear message.
- BR-Football-Dataset ends before the final rounds of the 2023 Serie A
  season (377 of 380 matches), so the calculated 2023 table reflects the data,
  not the official final table; output always states the match count and
  source file used.
- Libertadores has a few unplayed/`NA` rows; they are listed without scores
  and excluded from statistics.

## Specification

`TASK.md` / `brazilian-soccer-mcp-guide.md`

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
