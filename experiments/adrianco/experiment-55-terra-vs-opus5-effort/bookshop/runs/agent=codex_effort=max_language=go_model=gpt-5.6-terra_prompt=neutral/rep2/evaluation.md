# Evaluation: agent=codex effort=max language=go model=gpt-5.6-terra prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=gpt-5.6-terra, agent=codex, effort=max, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 test functions (TestHealth, TestBookCRUD, TestListBooksCanFilterByAuthor, TestBookValidation) / 0 failed / 0 skipped (4 effective)
- **Build:** pass (defect_rate=1.0 from scores.json ⇒ build + tests succeeded)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** run-summary skill unavailable in this session — see module notes below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Stored scores (`scores.json`): test_coverage=0.677, code_quality=1.0, defect_rate=1.0,
maintainability=0.801, idiomatic=0.87, token_efficiency=0.0216. `defect_rate=1.0`
confirms the build and full test suite passed; `test_coverage=0.677` is the Go coverage
fraction (not a pass/fail signal), so build/test were NOT re-run per the skill.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `handler.go:43-55` → `store.go:76` Create; all four fields persisted |
| R2 | GET /books lists all books | ✓ implemented | `handler.go:56-62` → `store.go:94` List |
| R3 | GET /books ?author= filter | ✓ implemented | `handler.go:57` reads query; `store.go:97-100` `WHERE author = ?`; test `handler_test.go:109` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `handler.go:82-87`; `store.go:129` maps sql.ErrNoRows→ErrNotFound→404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handler.go:88-97` → `store.go:139` Update; 404 when 0 rows affected |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handler.go:98-103` → `store.go:160` Delete; returns 204 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:9` `modernc.org/sqlite`; `store.go:40` sql.Open; table DDL `store.go:55` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `writeJSON` `handler.go:166`; 201/200/204/400/404/405 used throughout |
| R9 | Validation: title and author required | ✓ implemented | `handler.go:124-138` trims + rejects empty title/author with 400; test `handler_test.go:141` |
| R10 | GET /health health-check | ✓ implemented | `handler.go:26-31` returns `{"status":"ok"}`; test `handler_test.go:46` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — run, env vars, API table, test command |
| R12 | ≥3 unit/integration tests | ✓ implemented | 4 test functions in `handler_test.go`; test_coverage=0.677 > 0 |

## Build & Test

Not re-run (per evaluate-run skill step 2). Stored scores stand in:

```text
scores.json: defect_rate=1.0  ⇒  go build + go test ./... succeeded
             test_coverage=0.677  (coverage fraction, tests executed)
             code_quality=1.0  ⇒  lint clean
```

Test suite (from source, `handler_test.go`): 4 functions, 0 `t.Skip` calls.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 552 (.go incl. tests); 395 non-test |
| Files | 14 (10 source/config + go.mod/go.sum/README/TASK) |
| Dependencies | go.sum: 35 lines (single direct dep: modernc.org/sqlite) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; both are informational:

1. [info] POST /books sets a Location header on 201 — correct REST beyond spec
2. [info] Strict JSON decoding rejects unknown fields and trailing content — hardened validation

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=max_language=go_model=gpt-5.6-terra_prompt=neutral/rep2"
cat scores.json                                   # stored mechanical scores
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rE "^func Test" handler_test.go             # 4 test functions
# Optional re-verify (skill says do NOT re-run when scores exist):
# go test ./...
```
