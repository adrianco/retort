# Brazilian Soccer MCP Server

A dependency-free Rust MCP server over the six bundled Brazilian soccer CSV datasets. It loads match and FIFA player records into a normalized, read-only in-memory graph and exposes eleven tools for an LLM to search and analyze it.

## Build and verify

Rust 1.85 or newer is sufficient. The project has no third-party crates and does not need network access.

```sh
cargo build --release
cargo test
cargo run -- --check-data
```

`--check-data` validates all input files and prints loaded/skipped counts. Rows without enough information to identify a completed match (date, teams, season, and final score) are reported as skipped rather than silently converted to 0–0 results.

## Run as an MCP server

The default data directory is `data/kaggle` relative to the server's working directory:

```sh
cargo run --release
```

Use another location with either:

```sh
target/release/brazilian-soccer-mcp --data-dir /absolute/path/to/data/kaggle
BRAZILIAN_SOCCER_DATA_DIR=/absolute/path/to/data/kaggle target/release/brazilian-soccer-mcp
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/target/release/brazilian-soccer-mcp",
      "args": ["--data-dir", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

The process communicates only through newline-delimited MCP JSON-RPC on stdout. Startup diagnostics go to stderr. It supports the current `server/discover` lifecycle (protocol `2026-07-28`) and legacy `initialize` clients through `2025-11-25`, `2025-06-18`, and `2024-11-05`.

## Tools

| Tool | Answers |
|---|---|
| `dataset_info` | Loaded files, record counts, coverage, and capabilities |
| `search_matches` | Games by team/opponent, venue, date range, competition, season, final/stage, or source file |
| `team_statistics` | Wins/draws/losses, points, goals, goal difference, and win rate |
| `team_overview` | Cross-file club summary combining match competitions and FIFA players |
| `head_to_head` | Two-team meetings and aggregate record |
| `search_derbies` | Traditional rivalries such as Fla-Flu, Grenal, Derby Paulista, Ba-Vi, Re-Pa, and Atletiba |
| `search_players` | FIFA players by name, nationality, club, position group, and rating |
| `standings` | Calculated season tables with Brazilian league tie-break ordering |
| `competition_statistics` | Goal average and home/away/draw rates |
| `team_rankings` | Best home, away, or overall records |
| `biggest_wins` | Largest victory margins |

All tools return both concise text for a model and `structuredContent` JSON for programmatic use. Pagination is available on potentially large result sets. Tool definitions are annotated read-only, idempotent, non-destructive, and closed-world.

## Data behavior

- Team matching folds accents and case, understands state suffixes such as `Palmeiras-SP`, and maps common full forms such as `São Paulo Futebol Clube`.
- Ambiguous state-qualified names remain distinct (`Atlético-MG`, `Atlético-PR`, `Atlético-GO`, `América-MG`, and `América-RN`).
- ISO dates, timestamps, and Brazilian `DD/MM/YYYY` dates are normalized to `YYYY-MM-DD`.
- Cross-file result queries deduplicate the same match by date, competition, normalized teams, and score.
- Standings prefer the dedicated competition file for a season, preventing overlapping historical/extended datasets from doubling results.
- Copa do Brasil finals are inferred as the highest numbered round in each season because that CSV has round numbers but no stage names.
- The FIFA file is a historical snapshot. A player or club absent from it is reported as absent; the server does not invent or fetch live records.

The server uses only the bundled data. It cannot provide live scores, current rosters, individual match scorers (not present in these CSVs), or authoritative relegation rules beyond returning a calculated table.

## Direct protocol smoke test

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo","team_b":"Fluminense","limit":5}}}' \
  | cargo run --quiet
```

The integration tests load the real data, run more than twenty representative question shapes, verify the 2019 Brasileirão champion and identity normalization, and enforce the warm simple-query performance target.
