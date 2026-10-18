# Codebase summary

> `run-summary` skill is not invocable in this harness; this is a lightweight hand summary.

## Modules

- **`src/lib.rs`** (439 LoC) — the `brazilian_soccer_mcp` library. Holds the data model
  (`Match`, `Player`, `Record`), the in-memory `Database`, CSV loading, team-name
  normalization, and all query logic.
- **`src/main.rs`** (97 LoC) — a stdio JSON-RPC MCP server binary. Loads the database once
  at startup, then serves `initialize` / `tools/list` / `tools/call` over stdin/stdout.

## Interfaces

Tools registered by `schemas()` in `main.rs` and dispatched by `call()`:

| Tool | lib function | Purpose |
|------|--------------|---------|
| `search_matches` | `Database::search_matches` | filter matches by team/opponent/competition/season/date range |
| `team_statistics` | `Database::team_record` | W/L/D, goals for/against, win rate for a team |
| `head_to_head` | `Database::head_to_head_records` | two-team records + matches |
| `search_players` | `Database::search_players` | FIFA players by name/nationality/club/position |
| `standings` | `Database::standings` | season table computed from match results |

## Data flow

1. `Database::load(dir)` reads six CSVs from `data/kaggle/` via the `csv` crate, mapping each
   file's columns to the shared `Match` schema (and FIFA rows to `Player`). The five match
   files are concatenated into one `Vec<Match>`.
2. `normalize_team()` lower-cases, strips Portuguese accents, drops a trailing `-UF` state
   suffix, and removes `sport club` / `fc` tokens — used by match/record/h2h queries (but
   **not** by `standings`).
3. The server loop parses one JSON-RPC request per stdin line and replies on stdout.

## Notes

- `canonical_date` normalizes both `DD/MM/YYYY` and ISO datetime to `YYYY-MM-DD`.
- Tests live inline in `src/lib.rs` (`#[cfg(test)] mod tests`); `tests/` is empty.
