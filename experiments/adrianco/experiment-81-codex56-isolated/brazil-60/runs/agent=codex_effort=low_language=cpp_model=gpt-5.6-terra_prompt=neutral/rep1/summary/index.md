# Architecture Summary — brazilian-soccer-mcp (C++17)

Single translation unit, `main.cpp` (73 lines), dependency-free C++17. One `main.cpp` + `CMakeLists.txt`.

## Modules (all in `main.cpp`)

| Component | Lines | Role |
|-----------|-------|------|
| Text helpers (`trim`, `lower`, `normalize`) | 20–23 | Accent folding + state-suffix stripping for team-name matching |
| `csv()` | 24 | Quote-aware CSV tokenizer (handles `""` escapes, embedded commas) |
| `canonicalDate()` | 26–30 | Normalizes `DD/MM/YYYY` and ISO dates to `YYYY-MM-DD` |
| `Json` / `Parser` / `dump()` | 33–37 | Minimal JSON value, recursive-descent parser, serializer for JSON-RPC |
| `Match`, `Player`, `Database::load` | 39–51 | In-memory row structs; loads 5 match CSVs + FIFA player CSV via column-name maps |
| Query functions | 54–61 | `searchMatches`, `teamStats`, `h2h`, `players`, `standings`, `analyze`, `nl` (NL router) |
| `toolList` / `invoke` | 62–63 | MCP tool registry (7 tools) and dispatch |
| `selftest` | 64–72 | 5 inline BDD-style scenarios, wired as ctest `smoke` |
| `main` | 73 | stdio JSON-RPC loop: `initialize`, `tools/list`, `tools/call` |

## Data flow

stdin (newline-delimited JSON-RPC) → `Parser` → method dispatch → `invoke()` → one query function → text result wrapped in MCP `content` → `dump()` → stdout. Data loaded once at startup from `data/kaggle` (override via `SOCCER_DATA_DIR`).

## Interfaces

MCP tools exposed: `search_matches`, `team_statistics`, `head_to_head`, `search_players`, `standings`, `analyze`, `query`.

## Notes

Normalization (`normalize()`) is applied in the `contains()` filter used by searches, but **not** to the grouping keys in `standings()`, which key on raw team strings — see findings.
