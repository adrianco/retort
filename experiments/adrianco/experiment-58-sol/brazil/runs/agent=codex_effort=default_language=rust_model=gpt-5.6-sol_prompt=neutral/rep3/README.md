# Brazilian Soccer MCP Server

A fast, local Model Context Protocol server for the six Brazilian soccer CSV datasets bundled in this repository. It loads data once, normalizes team-name and date variations, deduplicates overlapping match sources, and returns both readable text and structured JSON to MCP clients.

## Build and test

```sh
cargo build --release
cargo test
cargo clippy --all-targets -- -D warnings
```

Dependencies are locked in `Cargo.lock`. In a network-restricted environment with a populated Cargo cache, add `--offline` to these commands.

Validate the datasets without starting the MCP transport:

```sh
cargo run --release -- --check
```

## Run

The default transport is MCP over standard input/output:

```sh
cargo run --release
```

The server finds data in `data/kaggle` by default. Override it with either:

```sh
cargo run --release -- --data-dir /path/to/kaggle
BRAZILIAN_SOCCER_DATA_DIR=/path/to/kaggle cargo run --release
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/target/release/brasileirao-mcp",
      "args": ["--data-dir", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

Logs go to stderr, leaving stdout exclusively for newline-delimited JSON-RPC messages.

## Tools

- `dataset_summary`: loading and coverage counts for every required file
- `search_matches`: team, opponent, competition, season, date range, stage/round, and source filters
- `team_statistics`: wins, draws, losses, goals, points, home/away records, and win rate
- `head_to_head`: meetings and aggregate rivalry record
- `search_players`: name, nationality, club, position, and minimum-rating filters
- `standings`: calculated table ordered by points, goal difference, then goals scored
- `competition_statistics`: goals per match and home/away/draw rates
- `biggest_wins`: largest victory margins
- `team_overview`: cross-file view joining match data, competitions, and FIFA club players

Team matching is case- and accent-insensitive and reconciles state suffixes and common full-name variants—for example, `São Paulo`, `Sao Paulo-SP`, and `São Paulo FC` resolve to the same team. Dates in ISO, ISO-with-time, and Brazilian `DD/MM/YYYY` formats are supported.

Only completed matches with parseable scores contribute to results and standings. `dataset_summary` reports parsed completed-row counts rather than raw line counts. Duplicate matches that appear in multiple source files are counted once in queries and aggregates; use the `source` filter on `search_matches` to inspect an individual file.
