# Evaluation: rest-api-crud (effort=low, model=claude-opus-5-5, prompt=neutral) · rep 3

## Summary

- **Factors:** language=elixir, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass (test_coverage=1.0 ⇒ build + all tests ran) — not re-run
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `router.ex:17`, `store.ex:62` INSERT + re-fetch |
| R2 | GET /books lists all | ✓ implemented | `router.ex:27`, `store.ex:50` |
| R3 | GET /books ?author= filter | ✓ implemented | `router.ex:30-36`, `store.ex:54` `WHERE author = ?1` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `router.ex:39`, `store.ex:97` fetch → `{:error, :not_found}` → 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `router.ex:48`, `store.ex:74`; missing id → fetch 404 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `router.ex:59`, `store.ex:86` returns 204; 404 if no rows changed |
| R7 | Data stored in SQLite | ✓ implemented | `store.ex` uses `Exqlite.Sqlite3`; `CREATE TABLE books` |
| R8 | JSON responses + status codes | ✓ implemented | `router.ex:100` JSON encode; 201/200/204/404/422/400/413 |
| R9 | Validation: title & author required | ✓ implemented | `book.ex:11-36` trims + rejects blank/missing → 422 (see finding) |
| R10 | GET /health | ✓ implemented | `router.ex:13` returns `{status: "ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Setup/Run/Test/API sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test/router_test.exs` — 14 tests; `test_coverage=1.0` |

## Build & Test

Build/test not re-run per skill guidance; scores read from `scores.json`:

```text
test_coverage = 1.0   # build + all tests executed and passed
code_quality  = 1.0
defect_rate   = 1.0
maintainability = 0.884
idiomatic     = 0.87
```

Skip scan (`grep` for `@tag :skip`/`:skip`/`xtest` in test/): 0 matches — no disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, lib+config) | 302 |
| Lines of code (tests) | 136 |
| Files (lib+test+config) | 8 |
| Dependencies | 4 (bandit, plug, jason, exqlite) |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] R9 validation failures return 422 while R9's `how_to_verify` mentions 400 — 422 is RFC-appropriate and documented in the README; no change required, noted for cross-run status-code comparison.

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=elixir_model=claude-opus-5-5_prompt=neutral/rep3"
cat scores.json                       # stored mechanical scores (no re-run)
grep -rEc "^\s*test " test/router_test.exs
grep -rE "@tag :skip|:skip|xtest" test/ | wc -l
# optional full re-run: mix deps.get && mix test
```
