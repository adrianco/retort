# Architecture summary — brazilian-soccer-mcp (Objective-C)

A self-contained ~223-line Objective-C MCP server (no network/DB) that serves the
supplied Kaggle CSVs as MCP tools over JSON-RPC/stdio.

## Modules

| File | Role |
|------|------|
| `main.m` | MCP transport + dispatch. Buffers stdin, splits on `\n`, parses each JSON-RPC frame, handles `initialize` / `tools/list` / `tools/call`, dispatches to `SoccerData`, writes newline-delimited replies (suppresses notifications with no `id`). |
| `SoccerData.h/.m` | Data layer. Loads 5 match CSVs + FIFA players, exposes the 7 query methods. |
| `tests/run_tests.sh` | 10 BDD-style integration scenarios driving the built binary over stdio. |
| `Makefile` | `clang -fobjc-arc -Wall -Wextra -Werror` build + `test` target. |

## Tools (registered in `main.m:40-42`)

`search_matches`, `team_statistics`, `head_to_head`, `search_players`,
`standings`, `competition_statistics`, `ask_brazilian_soccer` (7 total,
matching `_runtime.json` `tool_count: 7`).

## Data flow

1. `initWithDataDirectory:` loads all five match files into one `_matches` array,
   normalising column names per source and tagging each row with a `competition`.
   FIFA players are lazy-loaded on first player query.
2. `filtered:` applies team / opponent / competition / season / date-range / stage
   filters; team matching goes through `Fold()` (lowercase + diacritic-fold +
   strip `-SP/-RJ/...` suffixes and `FC`/`Futebol Clube`).
3. `standings:` aggregates W/D/L, points, goals from filtered matches, keyed on the
   **raw** home/away display string.

## Key transport fix (repair task)

The prior attempt dropped batched frames (multiple JSON-RPC messages in one stdin
read). `main.m` now accumulates a `pending` buffer and processes every complete
`\n`-terminated frame, plus a trailing non-terminated frame on EOF — verified by
the dedicated batch scenario in `run_tests.sh` (ids 101/102). `_runtime.json`
confirms the handshake now completes (`ok: true`).

## Known correctness gap

`standings:` groups by the raw team name, and `Fold()` does not reconcile the
`Athletico`↔`Atletico` spelling, so Athletico Paranaense appears as two split rows
in the 2019 Série A table (see `findings.jsonl` / `_factual.json`).
