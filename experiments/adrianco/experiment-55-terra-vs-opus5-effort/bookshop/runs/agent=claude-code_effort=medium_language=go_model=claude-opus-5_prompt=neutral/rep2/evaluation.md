# Evaluation: agent=claude-code_effort=medium_language=go_model=claude-opus-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-opus-5, agent=claude-code, effort=medium, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 20 test functions (all pass) / 0 failed / 0 skipped (20 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json); `go version go1.26.4`
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** run-summary skill unavailable in this session; module map inlined below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores from `scores.json`: test_coverage=0.76, code_quality=1.0, defect_rate=1.0,
maintainability=0.878, idiomatic=0.9, token_efficiency=0.030. `test_coverage=0.76`
is a coverage fraction (>0 ⇒ build + tests executed and passed); `defect_rate=1.0`
confirms build + test success.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.go:29,64` handleCreate → `store.go:69` Create; 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `server.go:30,83` handleList → `store.go:86` List |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:89` `WHERE author = ? COLLATE NOCASE`; `TestListAndAuthorFilter` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `server.go:31,95` handleGet → `store.go:116` Get → ErrNotFound→404 (`server.go:203`) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.go:32,108` handleUpdate → `store.go:132` Update; `TestUpdateBook` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.go:33,132` handleDelete → `store.go:156` Delete; 204; `TestDeleteBook` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:10` modernc.org/sqlite; `store.go:41` OpenStore; schema `store.go:25` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `server.go:215` writeJSON; 201/200/204/400/404/409/415/503 across handlers |
| R9 | Input validation: title & author required | ✓ implemented | `book.go:54-66` Validate → 400 `validationError`; `TestCreateValidation` |
| R10 | GET /health health-check | ✓ implemented | `server.go:28,49` handleHealth (pings DB, 503 on failure); `TestHealth` |
| R11 | README.md with setup & run instructions | ✓ implemented | `README.md` (6.3 KB) — setup/run/env/endpoints |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 20 `func Test*` across `server_test.go` + `store_test.go`; 0 skips |

No partial or missing requirements. Two info-level enhancements beyond spec
(ISBN validation + unique-ISBN 409, Content-Type/body-size hardening, graceful
shutdown) are recorded in `findings.jsonl`, not as deductions.

## Build & Test

Build/test not re-run — stored scores used per skill (defect_rate=1.0 ⇒ build+test pass).

```text
scores.json: {"code_quality":1.0,"test_coverage":0.76,"defect_rate":1.0,
              "maintainability":0.878,"idiomatic":0.9,"token_efficiency":0.030}
```

```text
Tests (grep of *_test.go): 20 Test functions, 0 t.Skip calls
server_test.go: Health, HealthUnavailableDB, Create, DistinctIDs, Validation,
  NonJSONContentType, DuplicateISBN, ListAndAuthorFilter, Get, Update, Delete,
  MethodNotAllowed, FullLifecycle
store_test.go: StoreCRUD, MissingRows, DuplicateISBN, PersistsAcrossReopen,
  ValidateNormalisesInput, ValidISBN, ValidateYearBoundaries
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (all .go) | 1270 |
| Source (non-test) LOC | book.go 127 + main.go 69 + server.go 225 + store.go 189 = 610 |
| Test LOC | server_test.go 475 + store_test.go 185 = 660 |
| Files (.go) | 6 |
| Dependencies (go.sum lines) | 51 (primary: modernc.org/sqlite) |
| Tests total | 20 |
| Tests effective | 20 |
| Skip ratio | 0% |
| Coverage (test_coverage) | 0.76 |

## Architecture

`run-summary` skill unavailable in this session. Module map:

- **main.go** — entry point: config via env (`ADDR`, `DB_PATH`), opens store, wires
  `http.Server` with timeouts, graceful SIGINT/SIGTERM shutdown.
- **server.go** — `Server` (routes via Go 1.22 method-pattern `ServeMux`), handlers,
  JSON encode/decode helpers, domain-error→HTTP-status mapping, request hardening.
- **store.go** — `Store`, SQLite schema + CRUD, ErrNotFound/ErrDuplicateISBN, unique
  ISBN partial index, case-insensitive author filter.
- **book.go** — `Book`, `BookInput` (pointer fields to distinguish absent vs empty),
  validation (required fields, year bounds, ISBN-10/13 shape/normalisation).

## Findings

Top items (full list in `findings.jsonl`):

1. [info] Validation/hardening beyond spec — ISBN format + unique 409, Content-Type & body-size limits
2. [info] Graceful shutdown and server timeouts in main.go

No critical/high/medium/low findings.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=claude-code_effort=medium_language=go_model=claude-opus-5_prompt=neutral/rep2"
cat scores.json                                   # stored build/test/lint scores
grep -rhoE "^func Test[A-Za-z0-9_]+" *_test.go     # 20 test funcs
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" # 0 skips
# (build/test intentionally NOT re-run; defect_rate=1.0 from scores.json)
```
