# Architecture Summary

> `run-summary` skill is not available in this session; this is a hand-written stand-in.

## Modules

- **`main.m`** — MCP server entrypoint. A line-delimited JSON-RPC 2.0 loop over
  stdin/stdout. Handles `initialize`, `notifications/initialized`, `tools/list`,
  and `tools/call`. Registers 6 tools (`search_matches`, `team_statistics`,
  `head_to_head`, `search_players`, `standings`, `competition_statistics`) with
  input schemas, dispatches each to a `SoccerDataStore` method, applies a `limit`
  cap, and wraps results as both `content` text and `structuredContent`.
- **`SoccerDataStore.{h,m}`** — in-memory data layer. On init it reads 5 match
  CSVs + `fifa_data.csv` from the data dir, normalizing heterogeneous column
  names (`home_team`/`home`/`Equipe_mandante`, `datetime`/`date`/`Data`, etc.)
  into a uniform match dict tagged with a `competition` label. Query methods
  filter/aggregate over the in-memory arrays.
- **`Tests/SoccerDataStoreTests.m`** — a `main()` that constructs the store and
  runs 7 `Check()` assertions (load counts, team match lookup, stats, H2H,
  player search, standings size), exiting non-zero on first failure.

## Key helpers

- `Key()` — team/competition normalization: diacritic-folds, lowercases, strips
  `-sp`/`-rj` suffixes only, removes non-alphanumerics. Used for fuzzy matching.
- `CSV()`/`ReadCSV()` — a quote-aware CSV parser.
- `DateOK()` — date-range filter on the first 10 chars (ISO day).

## Flow

stdin JSON-RPC → dispatch in `main.m` → `SoccerDataStore` query over preloaded
arrays → JSON result back to stdout.
