# Evaluation: agent=codex language=typescript model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=typescript, agent=codex, model=gpt-5.6-terra, prompt=neutral, effort=default
- **Task type:** REPAIR (a prior failing attempt was fixed in place)
- **Status:** ok — repaired run passes; both FEEDBACK defects resolved
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass (`npm run build` bundled into `npm test`; `defect_rate=1.0`)
- **Lint:** unavailable (no linter configured; `code_quality=0.733` from `scores.json`)
- **Factual accuracy:** 1.0 — 2019 Série A table correct (Flamengo 28W-6D-4L, 20/20 clubs) per `_factual.json`
- **Runtime:** cold start 352 ms, steady median 358 ms, 7 tools, first-query 21 ms (`_runtime.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `src/server.ts:27-42` (`initialize`/`tools/list`/`tools/call`/`resources/*` over stdio, `src/server.ts:60-72`), 7 tools each with concrete `inputSchema` `src/server.ts:10-22` |
| R2 | Load & use `data/kaggle/` datasets | ✓ implemented | `src/store.ts:18-39` reads all 6 CSVs via `parseCsv` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `src/store.ts:44` `sameTeam(home)||sameTeam(away)` |
| R4 | Filter by date range and/or season | ✓ implemented | `src/store.ts:46-47` season + `from`/`to` |
| R5 | Filter by competition | ✓ implemented | `src/store.ts:46` + competition union `src/types.ts:1`; 3 dedicated feeds |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `src/store.ts:57-66` `record()` |
| R7 | Player search by name | ✓ implemented | `src/store.ts:52-54` `searchPlayers({name})` |
| R8 | Filter players by nationality/club + ratings | ✓ implemented | `src/store.ts:52-54` accent-folded filters, sorted by `overall` |
| R9 | Season standings from match results | ✓ implemented | `src/store.ts:74-92` computed; single-feed dedup + `teamKey` grouping |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `src/store.ts:94-98` `statistics()` |
| R11 | Head-to-head between two teams | ✓ implemented | `src/store.ts:68-72` `headToHead()` |
| R12 | Automated tests covering queries | ✓ implemented | `test/store.test.ts` — 9 tests, execute & pass (`test_coverage=1.0`) |

## Build & Test

```text
npm test  →  npm run build && node --test test/*.test.ts
# build: import-checks src/*.ts under --experimental-strip-types (no emit)
# stored: test_coverage=1.0, defect_rate=1.0  (scores.json — not re-run per evaluate-run policy)
```

```text
9 node:test cases, 0 skipped. Coverage of: head-to-head + suffix normalization,
home record + computed standings, accented player search, MCP initialize/tools/call,
concrete input schemas, single-feed standings dedup, spawned stdio entrypoint,
all-datasets load, competition/season/date filtering + aggregate statistics.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + test) | 334 |
| Source files (src/ + test/) | 6 |
| Files (excl. data/, node_modules, tool caches) | 24 |
| Dependencies | 0 (stdlib only) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Cold start | 352 ms |
| Steady median request | 17.7 ms |

## Findings

Top items (full list in `findings.jsonl`) — no critical/high/medium:

1. [low] `sameTeam()` falls back to substring containment, risking over-broad matches (`src/normalization.ts:19-22`)
2. [low] `BR-Football-Dataset` rows all labelled `"Brazilian Football"`; the file's `tournament` column is unmapped (`src/store.ts:34`)
3. [info] Standings dedup + `teamKey` fix resolved the prior factual failure (`src/store.ts:74-92`)
4. [info] All MCP tools now declare concrete `inputSchema`s (`src/server.ts:10-22`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-60-terra-facts/brazil/runs/agent=codex_effort=default_language=typescript_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json _factual.json _runtime.json      # stored mechanical scores (do not re-run)
grep -rEn "\.skip\(|xit\(|it\.todo\(" src test    # skip audit → 0
# optional full run (rebuilds + runs tests):
npm test
```
