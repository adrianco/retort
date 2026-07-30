# Evaluation: go · claude-opus-5 · effort=high · prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-opus-5, agent=claude-code, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 test functions + 13 subtests, all passing / 0 failed / 0 skipped (all effective)
- **Build:** pass — `defect_rate=1.0` (scores.json)
- **Lint / quality:** pass — `code_quality=1.0`, `maintainability=0.86`, `idiomatic=0.87` (scores.json)
- **Coverage:** 75.7% statement coverage (`test_coverage=0.757`, scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Scores read from `scores.json` (inline gate eval — the high-effort rep2 row is
not yet in `retort.db`; the DB holds only effort=low/medium for this cell). No
build/test/lint was re-run, per the skill.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `api.go:101 createBook` → `store.go:87 Create` INSERT; `api_test.go:113 TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `api.go:121 listBooks` → `store.go:115 List`; `api_test.go:249` "all" subtest |
| R3 | GET /books supports ?author= filter | ✓ implemented | `store.go:118` `WHERE author = ? COLLATE NOCASE`; `api_test.go:263` filter subtests (incl. case-insensitive) |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `api.go:133 getBook`; `store.go:145 Get` → ErrNotFound→404; `api_test.go:298 TestGetBookNotFound` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `api.go:151 updateBook` → `store.go:158 Update`; `api_test.go:308 TestUpdateBook` (durability re-read) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `api.go:174 deleteBook` → `store.go:181 Delete` (204/404); `api_test.go:351 TestDeleteBook` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:12 modernc.org/sqlite`, schema+DSN; `book_test.go:169 TestStorePersistsAcrossReopen` proves disk persistence |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `api.go:268 writeJSON` sets JSON content-type; 200/201/204/400/404/405/409/413/415/422/500/503 used throughout; README status table |
| R9 | Input validation: title & author required | ✓ implemented | `book.go:39 Validate` (title/author required); `api_test.go:152 TestCreateBookValidation`. Rejects with `422` rather than the `400` in how_to_verify — see finding R9-note |
| R10 | GET /health health-check | ✓ implemented | `api.go:86 health` pings DB → 200/503; `api_test.go:98 TestHealth` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — setup, run, env vars, tests, full API + status-code docs |
| R12 | At least 3 unit/integration tests | ✓ implemented | 15 `Test*` functions across `api_test.go` (9) + `book_test.go` (6), 13 subtests; `test_coverage=0.757 > 0` |

## Build & Test

Not re-run — stored scores used as the build+test signal (per evaluate-run Step 2):

```text
scores.json: defect_rate=1.0  (build + all tests passed)
             test_coverage=0.757  (75.7% statement coverage)
             code_quality=1.0  maintainability=0.86  idiomatic=0.87
```

```text
Skip scan: grep -rE "t\.Skip\(|t\.Skipf\(" *.go  → 0 skipped/disabled tests
Test funcs: 15 (api_test.go=9, book_test.go=6); subtests via t.Run: 13
Effective tests = passed + failed - skipped = all effective (0 skips)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | ~697 (main/api/book/store.go) |
| Lines of code (tests) | ~613 |
| Files (source + tests + docs + go.mod/sum) | 10 tracked (17 incl. logs/meta) |
| Direct dependencies | 1 (`modernc.org/sqlite`; 9 indirect) |
| Tests total | 15 funcs + 13 subtests |
| Tests effective | all (0 skipped) |
| Skip ratio | 0% |
| Statement coverage | 75.7% |

## Findings

Top items by severity (full list in `findings.jsonl`) — all informational; no defects:

1. [info] R9-note — validation failures return `422` where the requirement's how_to_verify names `400`; still a correct rejection with an appropriate code.
2. [info] enh-hardening — panic-recovery middleware, 1 MiB body cap, strict JSON (DisallowUnknownFields), graceful shutdown, server timeouts.
3. [info] enh-isbn — ISBN-10/13 check-digit validation + normalization, partial unique index, duplicate-ISBN → 409.
4. [info] cov-note — 75.7% coverage; uncovered paths are mostly infra (`main.run()`, signal handling).

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=claude-code_effort=high_language=go_model=claude-opus-5_prompt=neutral/rep2"
cat scores.json                                    # stored build/test/quality signals
grep -rEn "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip scan → 0
grep -rEc "^func Test" *_test.go                   # test function counts
# Optional live check (not required — scores already stored):
go test ./...
```
