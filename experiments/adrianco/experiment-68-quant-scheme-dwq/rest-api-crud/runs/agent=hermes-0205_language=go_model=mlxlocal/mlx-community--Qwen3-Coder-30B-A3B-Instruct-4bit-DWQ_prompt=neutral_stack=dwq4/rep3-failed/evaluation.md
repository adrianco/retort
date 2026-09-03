# Evaluation: go · hermes-0205 · dwq4 · rep3 (SECOND OPINION)

## Summary

- **Factors:** language=go, model=mlxlocal/Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ, agent=hermes-0205, prompt=neutral, stack=dwq4
- **Status:** ok (builds + all 12 tests pass) — but one confirmed runtime routing defect breaks 3 endpoints
- **Requirements:** 9/12 implemented, 3 partial, 0 missing → requirement_coverage = **0.75**
- **Tests:** 12 total / 12 pass / 0 skipped (12 effective) — `test_coverage=0.597`, `defect_rate=1.0` from scores.json
- **Build:** pass — verified independently (`go build` succeeded, go1.26.6)
- **Lint:** `code_quality=0.9556` from scores.json
- **Findings:** 5 items in `findings.jsonl` (3 high, 1 medium, 1 info)

## Second-opinion verdict

The first evaluation is **CONFIRMED on all three disputed claims**. The burden of proof
was on "missing/unreachable", and I met it **empirically**, not just by reading code:
I copied the workspace to a temp dir, `go build`, ran the server on a verified-free port,
and probed it with curl.

| Endpoint | Live-server result | Verdict |
|----------|-------------------|---------|
| `POST /books` | `HTTP 201` + persisted body | works |
| `GET /books` | `HTTP 200` + list | works |
| `GET /books/1` (R4) | **`404 page not found`** | **unreachable** |
| `PUT /books/1` (R5) | **`404 page not found`** | **unreachable** |
| `DELETE /books/1` (R6) | **`404 page not found`** | **unreachable** |
| `GET /health` | `HTTP 200` `{"status":"healthy"}` | works |

`404 page not found` is the exact output of Go's default `http.NotFoundHandler` — proof
the `ServeMux` matched **no** registered pattern for `/books/1`. `main.go:268` registers
`http.HandleFunc("/books", …)`; a no-trailing-slash pattern is an **exact** path match, so
only `/books` reaches the handler. Inside it, `r.URL.Path == "/books"` (main.go:269) is
therefore always true, and the `else` branch (main.go:277-288) that dispatches
`getBookHandler`/`updateBookHandler`/`deleteBookHandler` is **dead code at runtime**.

The 12 green tests give false confidence: every by-id test calls the handler function
directly (e.g. `getBookHandler(w, req)` at main_test.go:195), bypassing the mux entirely.
No test serves through `http.DefaultServeMux`, so the bug is invisible to `go test`.
`test-api.sh:37` (`curl …/books/1`) *would* have caught it against a live server.

> Probe hygiene note: an initial probe on port 8099 was contaminated by a stray Python
> server **and** by this run's own agent-compiled `book-api` binary (still listening on
> `*:8099` from the agent session). Re-running on a verified-free port (8123) gave the
> clean result above. The contamination did not affect the verdict — the clean run
> confirms it.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `createBookHandler` main.go:126; live `POST /books` → 201, row persisted |
| R2 | GET /books lists all | ✓ implemented | `getBooksHandler` main.go:59; live `GET /books` → 200 |
| R3 | GET /books ?author= filter | ✓ implemented | main.go:69-71 `WHERE author LIKE ?`; TestGetBooksByAuthorFilter main_test.go:269 |
| R4 | GET /books/{id} single | ~ partial | Handler correct (main.go:98) but **unreachable** — live `GET /books/1` → `404 page not found` |
| R5 | PUT /books/{id} update | ~ partial | Handler correct (main.go:168) but **unreachable** — live `PUT /books/1` → `404 page not found` |
| R6 | DELETE /books/{id} delete | ~ partial | Handler correct (main.go:222) but **unreachable** — live `DELETE /books/1` → `404 page not found` |
| R7 | SQLite / embedded DB | ✓ implemented | `mattn/go-sqlite3` (main.go:12), `sql.Open("sqlite3", "./books.db")` main.go:30 |
| R8 | JSON responses + status codes | ✓ implemented | JSON encoders + 201/200/204/400/404/500 throughout; note by-id 404 falls to Go's plain-text default because the route is unreachable |
| R9 | Validation: title & author required | ✓ implemented | main.go:142-145; TestCreateBookValidation main_test.go:319 → 400 |
| R10 | GET /health | ✓ implemented | `healthHandler` main.go:52; live `GET /health` → 200 `{"status":"healthy"}` |
| R11 | README with setup/run | ✓ implemented | README.md — Setup, `go mod tidy`, `go run main.go`, endpoints, testing |
| R12 | ≥ 3 tests | ✓ implemented | 12 Test funcs in main_test.go, 0 skips, test_coverage=0.597 > 0 |

Implemented: 9 (R1,R2,R3,R7,R8,R9,R10,R11,R12). Partial: 3 (R4,R5,R6). Missing: 0.

## Metrics

| Metric | Value |
|--------|-------|
| Source files | main.go, main_test.go (+ go.mod/go.sum, README, test-api.sh) |
| Tests total | 12 |
| Tests effective | 12 (0 skipped) |
| Skip ratio | 0% |
| test_coverage (scores.json) | 0.597 |
| code_quality / maintainability | 0.9556 / 0.9141 |
| requirement_coverage | 9/12 = 0.75 |

## Findings

Top items (full list in `findings.jsonl`):

1. [high] R4 — GET /books/{id} unreachable at runtime (mux exact-match routing)
2. [high] R5 — PUT /books/{id} unreachable at runtime (same defect)
3. [high] R6 — DELETE /books/{id} unreachable at runtime (same defect)
4. [medium] Test suite calls handlers directly, so no test exercises the mux — bug passes 12 green tests
5. [info] 12 tests / 0 skips, well beyond the 3 required

## Reproduce

```bash
# copy out (do NOT modify run_dir), build, run on a free port, probe
cp main.go go.mod go.sum /tmp/gorun/ && cd /tmp/gorun
go build -o server . && PORT=8123 ./server &
curl -s -w '\n%{http_code}\n' -X POST -d '{"title":"T","author":"A"}' localhost:8123/books  # 201
curl -s -w '\n%{http_code}\n' localhost:8123/books/1     # 404 page not found  <-- R4 broken
curl -s -w '\n%{http_code}\n' -X PUT localhost:8123/books/1   # 404  <-- R5 broken
curl -s -w '\n%{http_code}\n' -X DELETE localhost:8123/books/1 # 404  <-- R6 broken
```
