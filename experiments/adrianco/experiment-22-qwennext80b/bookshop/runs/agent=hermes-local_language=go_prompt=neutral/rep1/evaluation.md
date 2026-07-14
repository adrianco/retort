# Evaluation: agent=hermes-local · language=go · prompt=neutral · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown, prompt=neutral
- **Status:** ❌ failed — the shipped server (`main.go`) panics on startup; the deliverable REST API does not run
- **Requirements:** 12/12 implemented at handler level, 0 partial, 0 missing — but none are reachable through the shipped `main.go`
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — via the test file's *own* gorilla/mux router, not `main.go`
- **Build:** pass — `go build` succeeds (test_coverage=0.621, defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (1 critical, 1 high, 1 medium, 1 low, 1 info)

The headline result: build and tests are green, but the tests silently paper over a critical wiring defect. `main.go` registers routes on a stdlib `http.NewServeMux()` with duplicate patterns, so the process **panics before serving any request**. The handlers themselves (which the tests exercise through a correct gorilla/mux router) are correct.

## Requirements

Pinned checklist from `bookshop/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handler/book_handler.go:CreateBook`, `model/book.go:CreateBook`; test `TestCreateBook` → 201 |
| R2 | GET /books lists all | ✓ implemented | `handler.ListBooks`, `model.ListBooks`; `TestListBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `ListBooks` reads `author` query; store filters `WHERE author LIKE ?`; `TestListBooksByAuthor` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `handler.GetBook` + `errors.New("book not found")`→404; `TestGetBook`, `TestGetBookNotFound` |
| R5 | PUT /books/{id} update | ✓ implemented | `handler.UpdateBook`, `model.UpdateBook` (RowsAffected→404); `TestUpdateBook` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `handler.DeleteBook`, `model.DeleteBook`; `TestDeleteBook`, `TestDeleteBookNotFound` |
| R7 | SQLite storage | ✓ implemented | `model/book.go` `sql.Open("sqlite3", ...)`, `mattn/go-sqlite3`, `CREATE TABLE books` |
| R8 | JSON + proper status codes | ✓ implemented | handlers set `Content-Type: application/json` + 201/200/204/400/404/500 |
| R9 | Validation: title & author required | ✓ implemented | `model.ValidateBook`; `TestCreateBookValidation` (also enforces year>0, isbn — see info finding) |
| R10 | GET /health | ✓ implemented | `handler.HealthCheck`→`{"status":"healthy"}`; `TestHealthCheck` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, curl examples) — but its run command crashes (see finding) |
| R12 | ≥3 tests | ✓ implemented | 11 test functions in `test/api_test.go`; test_coverage=0.621>0 |

> Caveat: R1–R10 are implemented in the handler/model layer and verified by the test harness, **but the shipped `main.go` never serves them** — it panics at startup. Requirement coverage is 12/12 at the code level; functional delivery is a critical failure captured in Findings.

## Build & Test

```text
go build ./...        # succeeds → produced ./bookapi (scores.json: test_coverage=0.621, defect_rate=1.0)
go test ./test/...    # 11 pass / 0 fail / 0 skip (tests use their own gorilla/mux router)
```

Runtime check of the shipped binary (run in scratchpad, run_dir untouched):

```text
$ ./bookapi
panic: pattern "/books" (registered at .../main.go:29) conflicts with pattern "/books"
       (registered at .../main.go:28): /books matches the same requests as /books
net/http.(*ServeMux).register(...)
main.main() .../main.go:29
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go, incl. tests) | 778 |
| Files (excl. built binary) | 15 |
| Dependencies (go.sum lines) | 4 (gorilla/mux, mattn/go-sqlite3) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build | pass |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. **[critical]** Server panics on startup — `main.go:28-29` register `/books` twice on `http.NewServeMux()`; confirmed runtime panic. Primary deliverable is non-functional.
2. **[high]** `main.go` uses stdlib ServeMux but handlers need gorilla/mux (`mux.Vars`, per-method routing) — broken even without the panic.
3. **[medium]** README's `go run main.go` instruction crashes immediately.
4. **[low]** README says Go 1.21+, `go.mod` requires `go 1.26.4`.
5. **[info]** Validation stricter than spec (also requires year>0, isbn).

## Reproduce

```bash
cd experiment-22-qwennext80b/bookshop/runs/agent=hermes-local_language=go_prompt=neutral/rep1
cat scores.json                              # stored mechanical scores (no re-build/test)
cp ./bookapi /tmp/bookapi-test && /tmp/bookapi-test   # observe the startup panic
grep -rEc "t\.Skip\(" . --include="*.go"     # 0 skips
grep -cE "^func Test" test/api_test.go       # 11 tests
```
