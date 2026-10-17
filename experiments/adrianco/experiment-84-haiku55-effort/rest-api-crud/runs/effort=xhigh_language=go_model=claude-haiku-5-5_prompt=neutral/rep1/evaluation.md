# Evaluation: effort=xhigh language=go model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, prompt=neutral, effort=xhigh
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 20 passed / 0 failed / 0 skipped (20 effective) — from `scores.json` (defect_rate=1.0)
- **Build:** pass — not re-run; `defect_rate=1.0`, `test_coverage=0.806` in `scores.json`
- **Lint:** pass — `code_quality=1.0` in `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.go:22,50` createBook → `store.go:62` Create; `server_test.go:54` |
| R2 | GET /books lists all | ✓ implemented | `server.go:69` listBooks → `store.go:94` List; `server_test.go:168` |
| R3 | GET /books ?author= filter | ✓ implemented | `server.go:70` query param → `store.go:97` WHERE author NOCASE; `store_test.go:79` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `server.go:79` getBook; `fail`→404 `server.go:196`; `server_test.go:156` |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.go:93` updateBook → `store.go:124` Update; `server_test.go:212` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `server.go:115` deleteBook → `store.go:142` Delete; `server_test.go:251` |
| R7 | Data in SQLite / embedded DB | ✓ implemented | `store.go:9,33` `modernc.org/sqlite` file-backed; `store_test.go:20` survives reopen |
| R8 | JSON responses + status codes | ✓ implemented | `server.go:208` writeJSON; 201/200/404/400/204/405/413 across handlers |
| R9 | Validation: title+author required | ✓ implemented | `book.go:37` Normalize; `book_test.go:10`, `server_test.go:92` |
| R10 | GET /health | ✓ implemented | `server.go:21,41` health (pings DB); `server_test.go:265` |
| R11 | README with setup/run | ✓ implemented | `README.md` Setup/Run/Test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 20 test funcs across 3 files; `test_coverage=0.806` |

## Build & Test

Not re-run per skill policy — stored mechanical scores stand in:

```text
scores.json
code_quality=1.0  test_coverage=0.806  defect_rate=1.0
maintainability=0.896  idiomatic=0.9  token_efficiency=0.0153
```

`defect_rate=1.0` ⇒ build + all tests passed. `test_coverage=0.806` is statement
coverage (not a pass/fail flag). 20 `Test*` functions, 0 `t.Skip` calls.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 548 (book 118, store 155, server 214, main 61) |
| Lines of code (tests) | 556 |
| Files (excl. .git) | 18 (incl. agent logs); 8 source/test .go |
| Dependencies | 1 direct (`modernc.org/sqlite`), 9 indirect; go.sum 50 lines |
| Tests total | 20 |
| Tests effective | 20 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All 4 are informational (no deductions):

1. [info] enh-1 — ISBN-10/13 checksum validation beyond spec (`book.go:76`)
2. [info] enh-2 — 405 + Allow header for known paths (`server.go:129`)
3. [info] enh-3 — Body-size cap, unknown-field rejection, graceful shutdown (`server.go:174`, `main.go:41`)
4. [info] note-put — PUT uses full-replacement semantics, documented + tested (`server.go:92`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=xhigh_language=go_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores
grep -rnE "^func (Test|Benchmark)" . --include="*.go" | wc -l   # 20 tests
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l     # 0 skips
# optional, builds+tests (not required — scores stored):
# go test ./...
```
