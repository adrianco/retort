# Architecture summary — brazilian-soccer-mcp (typescript, codex/gpt-5.6-terra)

Dependency-free TypeScript run on Node's `--experimental-strip-types`. ~334 LOC across 5 source files + 1 test file. This is the **repaired** run: both defects the FEEDBACK cited (empty MCP `inputSchema`s, double-counting standings) are fixed.

| Module | Role |
|--------|------|
| `src/types.ts` | `Match`, `Player`, `MatchFilter`, `Competition` type definitions. |
| `src/csv.ts` | Hand-rolled RFC-4180 CSV parser; `numberOrUndefined`, `isoDate` (handles `DD/MM/YYYY` and ISO). |
| `src/normalization.ts` | `normalise()` (accent-fold, strip `-UF` suffix, club ALIASES), `sameTeam()` fuzzy match, `teamKey()`/`displayTeamName()`. |
| `src/store.ts` | `SoccerStore` — loads 5 match CSVs + FIFA players into memory; query methods `findMatches`, `searchPlayers`, `record`, `headToHead`, `standings`, `statistics`. |
| `src/server.ts` | MCP JSON-RPC over stdio: `initialize` / `tools/list` / `tools/call` / `resources/list` / `resources/read`; 7 tools, each with a concrete `inputSchema`; NL `ask_question`. |
| `test/store.test.ts` | 9 `node:test` cases over a synthetic fixture, incl. a spawned-entrypoint stdio round-trip. |

## Flow

`server.ts` (stdin readline) → `handle(request, store)` → dispatches to `SoccerStore` methods → JSON-RPC result on stdout. `SoccerStore.load()` reads `data/kaggle/*.csv` at startup and normalises rows into a unified `Match[]` / `Player[]`.

## How the repaired defects were addressed

- **MCP schemas** — every tool now declares a typed `inputSchema` (`properties`, `required`, `additionalProperties:false`); a dedicated test asserts `search_matches.team` and `standings.required == ["season"]`.
- **Standings double-count** — `standings()` selects a single canonical Brasileirão feed (`serie-a`, else `historic`) so overlapping seasons aren't summed twice, and keys the table on `teamKey()` so `Flamengo` / `Flamengo-RJ` collapse to one row. Verified by the 2019 factual assertion (Flamengo 28W-6D-4L, 20/20 clubs) and a targeted dedup unit test.

## Residual notes (non-blocking)

`sameTeam()` uses substring containment as a fallback, which is permissive; and the `BR-Football-Dataset.csv` rows are all labelled competition `"Brazilian Football"` (the file's own `tournament` column is not mapped onto the three named competitions). Neither affects the graded requirements. See `findings.jsonl`.

(The `run-summary` skill is not registered as an invocable skill in this session; this summary was authored directly.)
