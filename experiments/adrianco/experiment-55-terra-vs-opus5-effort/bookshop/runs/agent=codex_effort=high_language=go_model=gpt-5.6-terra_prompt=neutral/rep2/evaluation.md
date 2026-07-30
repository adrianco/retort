# Evaluation: agent=codex_effort=high_language=go_model=gpt-5.6-terra_prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=gpt-5.6-terra, agent=codex, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — `defect_rate=1.0`, `test_coverage=0.639` from scores.json
- **Build:** pass — from `defect_rate=1.0` (not re-run)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** run-summary skill not available in this session; see inline notes below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Idiomatic Go stdlib implementation using Go 1.22+ routing patterns (`mux.HandleFunc("GET /books/{id}", ...)`) and the pure-Go `modernc.org/sqlite` driver. All CRUD routes, the author filter, validation, health check, README, and 3 integration tests are present. The mechanical scores confirm a clean build, passing tests, and clean lint.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.go:74 createBook` INSERTs title/author/year/isbn, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `server.go:41 listBooks` SELECTs all, returns JSON array |
| R3 | GET /books ?author= filter | ✓ implemented | `server.go:45` adds `WHERE author = ?`; test `server_test.go:82` |
| R4 | GET /books/{id} single book (404) | ✓ implemented | `server.go:93 getBook`; `server.go:99` returns 404 on `ErrNoRows` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.go:110 updateBook` UPDATEs, 404 if no rows |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.go:138 deleteBook`, 204 on success, 404 if absent |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:10,38` `modernc.org/sqlite`; schema in `main.go:46` |
| R8 | JSON responses + status codes | ✓ implemented | `server.go:207 writeJSON` sets Content-Type; 201/200/204/400/404/500 used |
| R9 | Validation: title & author required | ✓ implemented | `server.go:200` rejects empty title/author with 400; test `server_test.go:110` |
| R10 | GET /health | ✓ implemented | `server.go:37 health` returns `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` documents run, env vars, API, test |
| R12 | >= 3 unit/integration tests | ✓ implemented | 3 `func Test*` in `server_test.go`; `test_coverage=0.639` (ran) |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per evaluate-run Step 2):

```text
scores.json: {"code_quality": 1.0, "test_coverage": 0.639, "defect_rate": 1.0,
              "maintainability": 0.80, "idiomatic": 0.38, "token_efficiency": 0.037}
# defect_rate=1.0 => go build + go test ./... succeeded
# test_coverage=0.639 => tests executed with 63.9% coverage
```

Tests present (`server_test.go`): `TestBookCRUD`, `TestListBooksCanFilterByAuthor`,
`TestValidationAndHealth`. Skip scan (`t.Skip`/`t.Skipf`): 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 402 (main 58, server 215, test 129) |
| Files | 13 |
| Dependencies (go.sum lines) | 51 (1 direct: modernc.org/sqlite) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Strict JSON decoding beyond spec — `DisallowUnknownFields` + trailing-content rejection (enhancement)
2. [info] PUT performs full replace, resetting year/isbn if omitted — valid, documented semantics

No critical/high/medium/low findings. This is a complete, correct implementation.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=high_language=go_model=gpt-5.6-terra_prompt=neutral/rep2
cat scores.json                       # mechanical scores (build/test/lint)
grep -cE "^func Test" server_test.go  # test count = 3
grep -rE "t\.Skip" . --include="*.go" | wc -l  # skips = 0
# Optional full re-run: go test ./...
```
