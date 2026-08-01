# Evaluation: agent=codex language=clojure model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=clojure, agent=codex, model=gpt-5.6-terra, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 3 tests / 8 assertions — 0 failures / 0 errors / 0 skipped (8 effective)
- **Build:** pass — `test_coverage=1.0` from `scores.json` (build + all tests passed)
- **Lint:** pass — `code_quality=0.95` from `scores.json`; 1 low unused-symbol note
- **Architecture:** Ring handler (`core.clj`) + thin JDBC layer (`db.clj`) over SQLite; `run-summary` skill not available in this session
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Pinned checklist from `bookshop/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `core.clj:49-54` → `db/create-book!` `db.clj:36-46`, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `core.clj:46-47` → `db/list-books` `db.clj:48-53` |
| R3 | GET /books ?author= filter | ✓ implemented | `core.clj:47` reads `:params "author"`; `db.clj:50-53` WHERE author=? |
| R4 | GET /books/{id} single book | ✓ implemented | `core.clj:59-60` → `db/get-book`; 404 when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `core.clj:62-68` → `db/update-book!` `db.clj:58-62` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `core.clj:70-73` → `db/delete-book!`, returns 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `db.clj` JDBC via `org.sqlite.JDBC`; `deps.edn` sqlite-jdbc 3.46.1.3 |
| R8 | JSON responses + status codes | ✓ implemented | `core.clj:8-12` json-response; 201/200/400/404/204 used throughout |
| R9 | Validate title & author required | ✓ implemented | `core.clj:20-25` valid-book?; test asserts 400 `core_test.clj:37` |
| R10 | GET /health | ✓ implemented | `core.clj:43-44` returns `{status ok}`; test `core_test.clj:22-24` |
| R11 | README with setup/run | ✓ implemented | `README.md` documents `clojure -M:run`, env vars, endpoints, `clojure -M:test` |
| R12 | ≥3 unit/integration tests | ✓ implemented | 3 deftests / 8 assertions, `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run per evaluate-run skill §2):

```text
test_coverage = 1.0   → build + all tests passed
code_quality  = 0.95
defect_rate   = 0.756
```

Agent's own run (from `_agent_stdout.log`, item_15):

```text
clojure -M:test
Testing book-service.core-test
Ran 3 tests containing 8 assertions.
0 failures, 0 errors.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 194 (core 81, db 65, test-runner 8, test 40) |
| Files (src+test) | 4 |
| Dependencies | 5 (clojure, ring-core, ring-jetty-adapter, cheshire, sqlite-jdbc) |
| Tests total | 3 (8 assertions) |
| Tests effective | 3 (8 assertions) |
| Skip ratio | 0% |
| Build duration | n/a (scores cached) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Unused referred symbol `testing` in test ns — `core_test.clj:5`
2. [info] Malformed book ids rejected with 400 (enhancement) — `core.clj:55-57`
3. [info] Invalid JSON body handled gracefully → 400 not 500 (enhancement) — `core.clj:14-18`

No critical/high/medium findings. Clean, spec-complete run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-56-terra-alllang/bookshop/runs/agent=codex_effort=default_language=clojure_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json          # cached mechanical scores (test_coverage=1.0)
clojure -M:test          # 3 tests, 8 assertions, 0 failures/errors
```
