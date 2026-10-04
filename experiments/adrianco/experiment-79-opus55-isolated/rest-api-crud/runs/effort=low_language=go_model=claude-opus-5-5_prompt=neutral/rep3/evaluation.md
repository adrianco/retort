# Evaluation: rest-api-crud · effort=low language=go model=claude-opus-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `REQUIREMENTS.json`)
- **Tests:** 8 test functions, all pass / 0 failed / 0 skipped (8 effective) — coverage 79.4%
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** run-summary skill unavailable in this session; see module notes below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:19,66` createBook → `store.go:57` Create; 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:20,80` listBooks → `store.go:70` List |
| R3 | GET /books ?author= filter | ✓ implemented | `handlers.go:81`; `store.go:73-76` `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id} single book (404) | ✓ implemented | `handlers.go:21,89` getBook; `store.go:101-102` → ErrNotFound → 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:22,102` updateBook → `store.go:107` Update |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.go:23,119` deleteBook → `store.go:117` Delete; 204 |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:8` `modernc.org/sqlite`; CREATE TABLE + SQL persistence |
| R8 | JSON responses + status codes | ✓ implemented | `handlers.go:177` writeJSON; 201/200/204/400/404/422 used appropriately |
| R9 | title & author required | ✓ implemented | `handlers.go:46-51` validate(); rejects (422, see finding); tested `handlers_test.go:79` |
| R10 | GET /health | ✓ implemented | `handlers.go:18,58` health; pings DB, returns 200 `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, env vars, API table, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 8 `func Test*` in `handlers_test.go`; coverage 79.4% |

Prompt factor `neutral` adds no additional checkable requirements (it prescribes no
methodology and asks for tests demonstrating the requirements, covered by R12).

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.1189, "test_coverage": 0.794,
              "defect_rate": 1.0, "maintainability": 0.885, "idiomatic": 0.88}
```

- `defect_rate=1.0` ⇒ `go build` + `go test` succeeded.
- `test_coverage=0.794` ⇒ tests executed with 79.4% coverage (not the 0/1 gate).
- `code_quality=1.0` ⇒ lint/quality clean.
- Skip scan: `grep -E "t\.Skip\(|t\.Skipf\("` → 0 matches. No skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, no test) | 351 |
| Lines of code (incl. test) | 570 |
| Files (excl. .git) | 15 |
| Dependencies (go.sum lines) | 50 (1 direct: modernc.org/sqlite) |
| Tests total | 8 functions (TestCreateValidation has 7 sub-cases) |
| Tests effective | 8 (0 skipped) |
| Skip ratio | 0% |
| Coverage | 79.4% |

## Architecture (brief)

- `main.go` — entrypoint; opens `Store`, wires `http.Server` with `ReadHeaderTimeout`; ADDR/DB_PATH env config.
- `store.go` — SQLite persistence via `modernc.org/sqlite` (pure-Go, no CGO); `Store` with Create/List/Get/Update/Delete/Ping; `ErrNotFound` sentinel; single-conn for in-memory consistency.
- `handlers.go` — Go 1.22 `net/http` method+path routing; body validation, JSON encoding, status-code mapping; `MaxBytesReader` guard.
- `handlers_test.go` — table-driven httptest coverage of health, CRUD, author filter, validation, 404/bad-ID, and file persistence round-trip.

Clean separation (transport / persistence / entrypoint), idiomatic stdlib-only routing. run-summary skill was not available in this session, so no `summary/index.md` was generated.

## Findings

Full list in `findings.jsonl`. No critical/high/medium/low items; 2 informational notes:

1. [info] R9 — validation rejects with **422** where the spec's `how_to_verify` hinted **400** (defensible; 422 is semantically correct and documented in README; malformed JSON still returns 400).
2. [info] R3 — `?author=` is an exact case-insensitive match rather than substring (spec only requires a filter, satisfied).

## Reproduce

```bash
cd "$(git rev-parse --show-toplevel)/experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=go_model=claude-opus-5-5_prompt=neutral/rep3"
cat scores.json                                      # mechanical scores (not re-run)
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go"  # skip scan (0)
grep -rcE "^func Test" handlers_test.go              # test count
wc -l main.go store.go handlers.go handlers_test.go  # LOC
# To re-verify locally (optional; skill says do NOT re-run when scores exist):
# go test ./... -cover
```
