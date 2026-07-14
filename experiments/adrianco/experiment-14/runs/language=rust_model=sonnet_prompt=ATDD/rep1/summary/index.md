# Architecture Summary — brazilian-soccer-mcp (rust · sonnet · ATDD)

## Surface

A stdio JSON-RPC MCP server answering natural-language-style queries about Brazilian
soccer (matches, teams, players, competitions, statistics) over six pre-downloaded
Kaggle CSVs in `data/kaggle/`. The agent followed an ATDD style: the test suite is a
black-box acceptance suite that spawns the compiled binary and drives it over the MCP
protocol.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `src/main.rs` | MCP stdio loop: `initialize` / `tools/list` / `tools/call` JSON-RPC dispatch; tool schema declarations; data-dir discovery | `main()`, `tools_list()`, `call_tool()` |
| `src/data.rs` | CSV ingestion for all 6 datasets into `Vec<Match>` / `Vec<Player>`; per-file column parsers; goal/season/date parsing | `AppData::load()`, `load_*` parsers |
| `src/tools.rs` | The six query tools: filtering, aggregation, standings, H2H, stats; text formatting | `find_matches`, `get_team_stats`, `find_players`, `get_head_to_head`, `get_standings`, `get_statistical_summary` |
| `src/normalize.rs` | Team-name normalization (strips state suffixes) + fuzzy `teams_match`; 2 unit tests | `normalize_team_name()`, `teams_match()` |
| `tests/acceptance.rs` | Black-box ATDD suite: `McpTestServer` spawns the binary, MCP handshake, 10 acceptance tests | `McpTestServer`, 10 `#[test]` fns |

## Flow

`main()` discovers `data/kaggle` (env `SOCCER_DATA_DIR` or relative search), `AppData::load`
parses all CSVs into in-memory vecs, then a blocking stdin loop dispatches each JSON-RPC
line. `tools/call` routes to one of six pure functions in `tools.rs`, each of which scans
the in-memory `matches`/`players` vecs, filters/aggregates, and returns a formatted text
blob wrapped in MCP `content`.

## Interfaces

- **Transport:** newline-delimited JSON-RPC 2.0 over stdin/stdout (hand-rolled, no MCP SDK crate).
- **Tools:** 6 registered with JSON input schemas. All return human-readable text (not structured JSON content).
- **Data model:** `Match { datetime, home_team, away_team, home_goal, away_goal, season, round, competition, stage }`, `Player { name, age, nationality, overall, potential, club, value, position }`.

## Notable characteristics

- All six required CSVs are loaded and queried; competition tagging maps source files to `brasileirao` / `copa_brasil` / `libertadores`.
- The three Brasileirão sources overlap by season (2012–2019 duplicated across files) and are merged without dedup — see findings.
- Text-formatting uses byte-index slicing for truncation, which is not UTF-8-safe — see findings.
