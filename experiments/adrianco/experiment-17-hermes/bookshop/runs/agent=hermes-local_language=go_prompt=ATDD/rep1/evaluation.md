# Evaluation: agent=hermes-local language=go prompt=ATDD · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local, prompt=ATDD, framework=unknown (gorilla/mux + mattn/go-sqlite3)
- **Status:** ok — build + tests passed (defect_rate=1.0, code_quality=1.0 from scores.json)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Prompt (ATDD):** P1 followed (tests exercise the HTTP interface only); P2 violated (tests not isolated — shared on-disk DB)
- **Tests:** 6 effective (2 test funcs, 6 subtests) / 0 failed in scored run / 0 skipped — coverage 64.4% (test_coverage=0.644)
- **Build:** pass (from scores.json defect_rate=1.0 — not re-run)
- **Lint:** pass — code_quality=1.0 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 1 high, 2 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:createBook`; tested `main_test.go` "Create Book" |
| R2 | GET /books lists all | ✓ implemented | `handlers.go:getBooks`; tested "List Books" |
| R3 | GET /books ?author= filter | ✓ implemented | `handlers.go:26` `WHERE author = ?`; tested "Filter Books by Author" |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `handlers.go:getBook` returns 404 on `sql.ErrNoRows`; 404 asserted in CRUD flow step 6 |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:updateBook`; tested in CRUD flow (missing-id → 500, see finding) |
| R6 | DELETE /books/{id} | ✓ implemented | `handlers.go:deleteBook` (404 if 0 rows, else 204); tested |
| R7 | SQLite / embedded DB | ✓ implemented | `database.go` mattn/go-sqlite3, `./books.db` |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/404/400/204 across handlers; error bodies are plain text (see finding) |
| R9 | Validation: title & author required | ✓ implemented | `handlers.go:85`, `:135`; not covered by a test (see finding) |
| R10 | GET /health | ✓ implemented | `router.go` inline handler; tested "Health Check" |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, testing, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 subtests across `main_test.go` + `integration_test.go`; test_coverage=0.644 (>0) |

### Prompt-factor requirements (ATDD)

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Acceptance tests via public HTTP interface, assert behavior/status codes, no back-door DB access | ✓ implemented | Tests drive `initRouter` via `httptest`, assert status codes + JSON bodies; no direct DB queries in tests |
| P2 | Atomic & independent tests, each from an empty service, sharing no data | ~ partial | Tests share persistent `./books.db` with no reset; `integration_test.go:107` `assert.Len(...,1)` breaks on re-run; "List Books" depends on prior "Create Book" subtest |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
scores.json: code_quality=1.0, defect_rate=1.0, test_coverage=0.644,
             maintainability=0.836, idiomatic=0.48, token_efficiency=0.0083
```

`defect_rate=1.0` ⇒ `go build` + `go test ./...` succeeded in the scored run.
`test_coverage=0.644` is Go statement coverage (>0 ⇒ tests executed; the
uncovered ~36% is mostly error branches, incl. the untested validation path).

Test inventory (grepped, not executed):

```text
func TestBookAPI            (main_test.go)        — 4 subtests: Health, Create, List, Get
func TestBookAPIIntegration (integration_test.go) — 2 subtests: Complete CRUD Flow, Filter by Author
skipped tests: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, .go excl. tests) | 285 |
| Lines of code (tests) | 206 |
| Files (excl. .git) | 20 (incl. built `book-api` binary + `books.db`) |
| Source modules | 4 |
| Dependencies (direct) | 3 (gorilla/mux, go-sqlite3, testify) |
| Tests effective | 6 (2 funcs / 6 subtests) |
| Skip ratio | 0% |
| Build | pass (not re-run) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. **[high]** Acceptance tests are not isolated — they share the persistent `./books.db`, so the suite is non-repeatable (`integration_test.go:107` `assert.Len(...,1)` fails on a second run). Directly violates the ATDD prompt's "each scenario starts from a running but empty service."
2. **[medium]** `PUT /books/{id}` on a non-existent id returns 500 instead of 404 (`handlers.go:150` maps `sql.ErrNoRows` to Database error; never checks RowsAffected).
3. **[medium]** Error responses are plain text via `http.Error`, contradicting the `application/json` Content-Type header and R8's "JSON responses".
4. **[low]** Validation (R9) is implemented but has no negative test asserting 400 on a missing title/author.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-17-hermes/bookshop/runs/agent=hermes-local_language=go_prompt=ATDD/rep1
cat scores.json                                   # stored mechanical scores (no re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rE "^func Test" . --include="*.go"          # test inventory
# optional fresh verify (mutates books.db — copy out first):
#   tmp=$(mktemp -d); cp *.go go.* "$tmp"/; (cd "$tmp" && go test ./...)
```
