# Architecture: Brazilian Soccer MCP Server (C)

A self-contained MCP server in portable C11 with **no external dependencies** —
its own CSV parser, JSON parser/writer, and data layer. ~2,890 LOC across 9 files.

## Modules

| File | LOC | Responsibility |
|------|-----|----------------|
| `bsmcp.h` | 146 | Shared declarations: `CsvFile`, `JVal`, `SB` string builder, `Match`, `Player`, `DB`, `ToolDef`. |
| `csv.c` | 159 | RFC-4180-ish CSV loader — quoted fields, escaped `""`, embedded newlines, UTF-8 BOM skip. `csv_col()` maps header names to indices. |
| `json.c` | 417 | Recursive-descent JSON parser (`json_parse`) + growable string builder (`SB`) with `sb_json_str` escaping for output. |
| `data.c` | 590 | Loads the 6 Kaggle CSVs into `DB`; name normalization (accent folding, state-suffix stripping, club aliasing), date parsing (ISO + `DD/MM/YYYY`), `name_matches` suffix-aware matcher. |
| `tools.c` | 934 | The 7 MCP tools + `tool_dispatch`. Match filtering (`collect`), team records (`Rec`), standings computation, player search/sort. |
| `mcp_main.c` | 195 | JSON-RPC 2.0 stdio transport: `initialize`, `ping`, `tools/list`, `tools/call`, `notifications/*`. |
| `test_main.c` | 449 | 75 `check()` assertions + a ≥20 sample-question gate + performance gates. |
| `test_mcp.sh` | — | End-to-end stdio protocol smoke test (initialize + tools/call over pipes). |
| `Makefile` | — | Builds `bsmcp` and `test_bsmcp`; `make test` runs both suites. |

## MCP tools (registered in `TOOLS[]`)

`search_matches`, `get_team_stats`, `head_to_head`, `search_players`,
`get_standings`, `get_league_stats`, `list_competitions` — each with a full JSON
Schema `inputSchema` surfaced via `tools/list`.

## Data flow

`main()` → `db_load("data/kaggle")` loads 5 match CSVs (23,954 matches) +
`fifa_data.csv` (18,207 players) → stdio loop reads one JSON-RPC message/line →
`tool_dispatch` filters/aggregates over in-memory arrays → text content returned
in an MCP `content[]` block. All queries are in-memory linear scans; the test
suite asserts simple lookups < 2s and aggregates < 5s.
