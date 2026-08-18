# Architecture summary — brazilian-soccer-mcp (typescript, codex/gpt-5.6-terra)

Dependency-free TypeScript run on Node's `--experimental-strip-types`. ~258 LOC across 5 source files + 1 test file.

| Module | Role |
|--------|------|
| `src/types.ts` | `Match`, `Player`, `MatchFilter`, `Competition` type definitions. |
| `src/csv.ts` | Hand-rolled RFC-4180 CSV parser; `numberOrUndefined`, `isoDate` (handles `DD/MM/YYYY` and ISO). |
| `src/normalization.ts` | `normalise()` (accent-fold, strip `-UF` suffix, club ALIASES) and `sameTeam()` fuzzy match. |
| `src/store.ts` | `SoccerStore` — loads 5 match CSVs + FIFA players into memory; query methods `findMatches`, `searchPlayers`, `record`, `headToHead`, `standings`, `statistics`. |
| `src/server.ts` | MCP JSON-RPC over stdio: `initialize` / `tools/list` / `tools/call`; 7 tools incl. NL `ask_question`. |
| `test/store.test.ts` | 5 node:test cases over a synthetic fixture. |

## Flow

`server.ts` (stdin readline) → `handle(request, store)` → dispatches to `SoccerStore` methods → JSON-RPC result on stdout. `SoccerStore.load()` reads `data/kaggle/*.csv` at startup and normalises rows into a unified `Match[]` / `Player[]`.

## Key architectural weakness

The five match files are concatenated into one array with **no deduplication**, and `standings()` keys the table on the **raw** team name. Seasons present in two source files (e.g. 2019 in both `Brasileirao_Matches.csv` and `novo_campeonato_brasileiro.csv`) are double-counted and team names split across suffix variants — the root cause of `factual_accuracy=0.0`. See `findings.jsonl` R9/R10.

(The `run-summary` skill is not registered as an invocable skill in this session; this summary was authored directly.)
