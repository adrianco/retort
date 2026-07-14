# Evaluation: language=go_model=claude-fable-5 · rep 1

## Summary

- **Factors:** language=go, model=claude-fable-5
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=0.731, defect_rate=1.0 from scores.json
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** summary skill unavailable
- **Findings:** 0 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 0 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✓ implemented | `server.go:80` handleCreate; `store.go:53` Create INSERT; `server_test.go:57` TestCreateAndGetBook |
| R2 | GET /books lists all books | ✓ implemented | `server.go:94` handleList; `store.go:66` List SELECT; `server_test.go:117` TestListWithAuthorFilter |
| R3 | GET /books supports ?author= filter | ✓ implemented | `server.go:95` `r.URL.Query().Get("author")`; `store.go:69` WHERE clause; `server_test.go:122` filter assertion |
| R4 | GET /books/{id} returns single book | ✓ implemented | `server.go:103` handleGet with 404; `store.go:92` Get; `server_test.go:74` get-by-id test |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.go:121` handleUpdate; `store.go:106` Update; `server_test.go:134` TestUpdateBook |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.go:145` handleDelete returns 204; `store.go:124` Delete; `server_test.go:155` TestDeleteBook |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` imports `modernc.org/sqlite`; `store.go:29` `sql.Open("sqlite", path)`; `store.go:37` CREATE TABLE |
| R8 | JSON responses with HTTP status codes | ✓ implemented | `server.go:32` writeJSON sets Content-Type; codes: 201/200/204/400/404/500 |
| R9 | Input validation: title and author required | ✓ implemented | `server.go:57-68` decodeBook validates non-empty after trim; `server_test.go:84` TestCreateValidation |
| R10 | GET /health health-check endpoint | ✓ implemented | `server.go:76` handleHealth returns `{"status":"ok"}`; `server_test.go:45` TestHealth |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents Go 1.22+ setup, `go run .`, `go test ./...`, env vars, API table |
| R12 | At least 3 unit/integration tests | ✓ implemented | 7 test functions in `server_test.go`: Health, CreateAndGet, Validation, ListFilter, Update, Delete, InvalidID |

## Build & Test

```text
Build/test scores read from scores.json (not re-run per skill policy):
  test_coverage:   0.731
  defect_rate:     1.0   (1.0 = build+test succeeded)
  code_quality:    1.0
  maintainability: 0.894
  idiomatic:       0.870
  token_efficiency: 0.045
```

```text
7 test functions, 0 skipped, 0 skip markers found.
Tests use httptest.NewRequest/httptest.NewRecorder with temp SQLite DBs.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 509 (Go) |
| Files | 13 |
| Dependencies | 21 (go.sum entries) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (scores from scores.json) |

## Findings

No findings. All 12 requirements implemented; build, tests, and lint pass cleanly.

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=go_model=claude-fable-5/rep1
cat scores.json
cat stack.json
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
grep -cE "func Test" server_test.go
find . -type f -not -path "*/.git/*" | wc -l
grep -c "^\s*\S" go.sum
```
