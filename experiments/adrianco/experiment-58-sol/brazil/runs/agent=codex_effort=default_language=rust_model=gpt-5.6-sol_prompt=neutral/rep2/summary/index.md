# Architecture Summary — brazilian-soccer-mcp (rust)

A stdio JSON-RPC MCP server over the supplied Kaggle Brazilian-soccer datasets.

## Modules (`src/`)

| File | Role |
|------|------|
| `main.rs` | Entrypoint: resolves data dir (`BRAZILIAN_SOCCER_DATA_DIR` or bundled `data/kaggle`), loads the store, prints a load banner to stderr, serves stdio. |
| `mcp.rs` | JSON-RPC 2.0 framing over stdin/stdout: `initialize`, legacy/stateless protocol negotiation, `server/discover`, `tools/list`, `tools/call`, `ping`. Defines the 7 tool schemas. |
| `query.rs` | `SoccerService` — the query engine. Implements `search_matches`, `get_team_record`, `get_head_to_head`, `search_players`, `analyze_competition` (standings/summary/biggest_wins/team_ranking), `get_standings`, and an `ask_soccer` NL router. |
| `data.rs` | `DataStore::load` — reads 5 match CSVs + `fifa_data.csv`, normalizes rows, deduplicates matches by a source-aware key, merges optional fields, builds a team-name map. |
| `normalize.rs` | Text/accent folding, `team_key` canonicalization (strips state suffixes + club words, alias table), `competition_key`, multi-format date parsing. |
| `domain.rs` | Data types: `SoccerMatch`, `Player`, `TeamRecord`, `Standing`, `MatchMetrics`. |

## Data flow

CSV files → per-source `parse_match` → dedup by `(competition, season, teams, score)` (Brasileirão) or `(…, date, …)` (others) → in-memory `Vec<SoccerMatch>` + `Vec<Player>` → `SoccerService` filters/aggregates → JSON-RPC results with `structuredContent` + a text summary.

## Tools exposed (7)

`search_matches`, `get_team_record`, `get_head_to_head`, `search_players`, `analyze_competition`, `get_standings`, `ask_soccer`.

## Tests

- `tests/protocol.rs` — MCP protocol lifecycle/framing.
- `tests/real_data.rs` — loads the real datasets and asserts match/team/player/standings/NL query answers (e.g. 2019 champion = 90 points, 380 matches).
- Plus in-module unit tests in `mcp.rs`, `query.rs`, `data.rs`, `normalize.rs`. 12 `#[test]` total, 0 ignored.
