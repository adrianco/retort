# Run Summary — brazilian-soccer-mcp (C · codex · gpt-5.6-terra)

## Surface

A dependency-free MCP (Model Context Protocol) server written in a single C11
translation unit. It speaks JSON-RPC 2.0 over stdin/stdout (one JSON object per
line), loads six Kaggle CSV datasets at startup, and exposes six query tools over
Brazilian soccer match and FIFA player data.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `brazilian_soccer_mcp.c` | Whole server: CSV loader, normalizer, 6 tools, JSON-RPC dispatch | `main`, `load_data`, `handle` |
| `Makefile` | Build (`cc -std=c11 -O2 -Wall -Wextra -Wpedantic`) + `make test` | `all`, `test` |
| `tests.sh` | BDD-style smoke test driving the built binary via JSON-RPC | shell script |
| `data/kaggle/*.csv` | 6 provided datasets (matches + FIFA players) | data |

## Internal structure (single file)

- **Storage**: two growable arrays — `Matches` (Match structs) and `Players`
  (Player structs), built by `pushm`/`pushp` with amortized doubling.
- **CSV**: `csv()` is an RFC-4180-ish reader (handles quotes, `""` escapes, CRLF);
  `col()`/`field()` resolve columns by header name so schema differences between the
  historic (`Equipe_mandante`…) and current (`home_team`…) CSVs are absorbed.
- **Normalization**: `norm()` lowercases, strips accents (UTF-8 0xC3 pairs → ASCII),
  drops punctuation and state suffixes; `team_eq` (substring) and `same_team` (exact)
  build on it. `canon_date()` folds `DD/MM/YYYY` → `YYYY-MM-DD`.
- **Tools**: `tool_matches`, `tool_team`, `tool_head`, `tool_players`,
  `tool_standings`, `tool_stats`, plus a static `tools_json` catalogue.
- **JSON**: hand-rolled `json_get`/`argint` argument extraction and `jsonstr`/`esc`
  output; `handle()` dispatches `initialize` / `tools/list` / `tools/call`, capturing
  tool output via `open_memstream` and re-emitting it as an MCP text content block.

## Control flow

`main(dir)` → `load_data` (6 CSVs) → line loop over stdin → `handle` → JSON-RPC
method dispatch → tool function writes JSON into an in-memory stream → wrapped as
`result.content[].text` → flushed to stdout.

## Notes for cross-run comparison

- Extremely compact: 72 LOC implements all six capability areas with zero external
  dependencies (only libc). Very high idiomatic density; low readability per line.
- Standings de-duplicate the overlapping historic/current Brasileirão CSVs by year.
- Tests are a thin smoke test (see `../findings.jsonl`), not correctness assertions.
