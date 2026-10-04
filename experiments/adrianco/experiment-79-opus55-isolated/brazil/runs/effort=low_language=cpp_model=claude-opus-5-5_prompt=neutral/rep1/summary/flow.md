# Control Flow

1. `main` resolves the data directory (`--data` → `$BRAZILIAN_SOCCER_DATA` → `./data/kaggle`
   → build-tree source) and calls `Database::load`.
2. `Database::load` reads each CSV via `parseCsv`, normalizes team names (`parseTeamName`,
   alias table, state suffixes) and dates (`normalizeDate`), interns teams, appends `Match`
   rows, then merges duplicate matches across files and sorts by date. FIFA players are
   loaded and linked to teams where the club name matches.
3. `mcp::Server` runs a newline-delimited JSON-RPC 2.0 loop on stdin/stdout:
   `initialize` → `tools/list` → `tools/call`. Each tool handler parses its arguments,
   resolves team names via `findTeam`, builds a `MatchFilter`/`PlayerFilter`, calls the
   corresponding `Database` query, and renders a text result.
4. `--call <tool> <json>` bypasses the loop for a single one-shot invocation.
