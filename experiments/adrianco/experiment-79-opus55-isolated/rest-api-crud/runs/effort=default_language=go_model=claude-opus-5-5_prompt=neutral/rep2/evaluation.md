# Evaluation: rest-api-crud · effort=default language=go model=claude-opus-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-opus-5-5, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** all passed / 0 failed / 0 skipped (8 test functions, effective) — `test_coverage=0.753` from retort.db
- **Build:** pass — `defect_rate=1.0`, `test_coverage=0.753` from retort.db (not re-run)
- **Lint:** pass — `code_quality=1.0` from retort.db
- **Architecture:** `run-summary` skill not registered as invocable; brief note below
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info) — all enhancements/notes

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (constant 12-item denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `handlers.go:57,74` createBook → `store.go:60` Create |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:58,88` listBooks → `store.go:75` List |
| R3 | GET /books ?author= filter | ✓ implemented | `handlers.go:89`; `store.go:78-81` WHERE author COLLATE NOCASE; tested `handlers_test.go:146-148` |
| R4 | GET /books/{id} single book, 404 if absent | ✓ implemented | `handlers.go:59,97` getBook; `store.go:107` ErrNotFound → 404 `handlers.go:180` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:60,110` updateBook → `store.go:114` Update |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:61,127` deleteBook → `store.go:133` Delete; 204 |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:8,41` `modernc.org/sqlite`; schema `store.go:28`; persistence test `handlers_test.go:248` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `handlers.go:188` writeJSON; 201/200/404/400/204/405 used throughout |
| R9 | Validation: title and author required | ✓ implemented | `handlers.go:24-40` validate; tested `handlers_test.go:83-127` |
| R10 | GET /health health check | ✓ implemented | `handlers.go:56,65` health (pings DB); tested `handlers_test.go:48` |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` — setup, env vars, tests, endpoint table |
| R12 | ≥3 unit/integration tests | ✓ implemented | 8 `Test*` functions in `handlers_test.go` |

No requirements missing, partial, or cannot-verify.

## Build & Test

Scores read from `retort.db` / `scores.json` (per skill, toolchain not re-run):

```text
defect_rate    = 1.0    (build + tests succeeded)
test_coverage  = 0.753  (tests executed and passed; 75.3% coverage)
code_quality   = 1.0    (lint clean)
requirement_coverage = 1.0
idiomatic      = 0.88 / maintainability = 0.886
```

Test inventory (grepped, not executed): 8 test functions, 0 `t.Skip` calls.
`TestHealth`, `TestCreateAndGetBook`, `TestCreateBookValidation`, `TestListBooks`,
`TestUpdateBook`, `TestDeleteBook`, `TestBookIDErrors`, `TestStorePersistsAcrossReopen`
— table-driven subtests add further coverage of filter, validation, and id-error cases.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .go) | 671 (396 non-test) |
| Files (excl. .git) | 15 (4 .go + go.mod/go.sum/README/.gitignore) |
| Dependencies (go.sum lines) | 50 (1 direct: modernc.org/sqlite; rest indirect) |
| Tests total | 8 functions (+ table subtests) |
| Tests effective | 8 (0 skipped) |
| Skip ratio | 0% |
| Build duration | not re-run (read from retort.db) |

## Architecture (inline)

`run-summary` is not registered as an invocable skill in this session, so a brief note in its place:

- **`main.go`** — wiring: reads `PORT`/`BOOKS_DB` env, opens the store, builds the `http.Server`
  with sane timeouts, and runs a graceful shutdown loop on SIGINT/SIGTERM.
- **`store.go`** — `Store` over `database/sql` + `modernc.org/sqlite` (pure-Go driver, no cgo).
  Schema with an author index; `Create/List/Get/Update/Delete` plus `Ping`. `MaxOpenConns(1)`
  serialises writes and keeps `:memory:` consistent across requests. `ErrNotFound` sentinel.
- **`handlers.go`** — `Server` with a Go 1.22+ method-pattern `ServeMux`. Input struct with
  `validate()`, hardened `decodeBook` (body cap, single-object, typed errors), and a central
  `writeStoreError` mapping `ErrNotFound`→404.
- **`handlers_test.go`** — httptest-driven handler tests plus a real-file reopen persistence test.

Clean layering (main → handlers → store); the store has no HTTP knowledge.

## Findings

All 4 findings are informational (enhancements beyond spec / neutral notes); none affect scoring:

1. [info] Graceful shutdown with signal handling and server timeouts (`main.go:33-43,27-30`)
2. [info] Robust request decoding: body size cap, single-object enforcement, typed errors (`handlers.go:154,168`)
3. [info] Location header on create; 405 for unmapped methods (`handlers.go:84`; test `:243`)
4. [info] PUT is a full replace (title+author required), not a partial patch (`handlers.go:110`) — acceptable per spec

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=default_language=go_model=claude-opus-5-5_prompt=neutral/rep2"
cat scores.json                                   # stored mechanical scores (build/test not re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rE "^func Test" *.go                         # 8 test functions
# cross-check DB:
sqlite3 -readonly ../../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr JOIN experiment_runs er ON er.id=rr.run_id WHERE json_extract(er.run_config_json,'\$.language')='go' AND json_extract(er.run_config_json,'\$.model')='claude-opus-5-5' AND er.replicate=2;"
```
