# Evaluation: agent=hermes-0222_language=go_model=llamacpp/Holo4-35B-A3B_prompt=neutral_stack=holo4 · rep 1

*Second-opinion re-check (2026-10-19) of a prior evaluation that scored requirement_coverage=0.9167 with R7 not met.*

## Summary

- **Factors:** language=go, agent=hermes-0222, model=llamacpp/Holo4-35B-A3B, prompt=neutral, stack=holo4
- **Status:** ok
- **Requirements:** 11/12 implemented, 1 partial (R7), 0 missing — pinned `REQUIREMENTS.json`
- **Tests:** 10 test functions (+subtests in TestCreateBookValidation), 0 skipped; test_coverage=0.505 from `scores.json` (tests ran and passed; defect_rate=1.0)
- **Build:** pass (defect_rate=1.0, from `scores.json`; not re-run)
- **Lint:** code_quality=0.956 (from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 3 low)

## Second opinion on the prior claim

**R7 — CONFIRMED not fully met.** I looked for any persistence or connection-pinning that would rescue `:memory:`: `grep` for `SetMaxOpenConns`, `cache=shared`, `DB_PATH`, `Setenv` across `*.go` and README found nothing. The only `sql.Open` is `main.go:41` with `":memory:"` (the test helper `main_test.go:14` does the same). database/sql pools connections and each new SQLite `:memory:` connection is a fresh, empty database, so the `CREATE TABLE` at `main.go:55` exists on only one connection. An independent probe (temp copy, 50 concurrent `GET /books` through `booksHandler`, 3 runs) returned `500` for 49, 46 and 48 of 50 requests. And data is lost on every restart, which contradicts the checklist's "not just in-memory state". It *does* use SQLite, so this is `partial`, not `missing`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates | ✓ implemented | `main.go:77 createBookHandler`; `TestCreateBook` |
| R2 | GET /books lists | ✓ implemented | `main.go:127 listBooksHandler`; `TestListBooks` |
| R3 | ?author= filter | ✓ implemented | `main.go:133-137`; `TestListBooksAuthorFilter` |
| R4 | GET /books/{id} | ✓ implemented | `main.go:177`, 404 at :195; `TestGetBook`, `TestGetBookNotFound` |
| R5 | PUT /books/{id} | ✓ implemented | `main.go:206` partial update; `TestUpdateBook` |
| R6 | DELETE /books/{id} | ✓ implemented | `main.go:299`; `TestDeleteBook`, `TestDeleteBookNotFound` |
| R7 | SQLite / embedded DB persistence | ~ partial | `main.go:41` `:memory:` — no persistence; pooled connections lack the table (probe: 46-49/50 → 500) |
| R8 | JSON + proper status codes | ✓ implemented | `writeJSON`/`writeError` `main.go:59-67`; 201/200/400/404/405/204 (204 carries a `null` body — low) |
| R9 | title & author required | ✓ implemented | `main.go:89-96` → 400; `TestCreateBookValidation` (also requires year/isbn — stricter than spec, low) |
| R10 | GET /health | ✓ implemented | `main.go:69`; `TestHealthEndpoint` |
| R11 | README setup/run | ✓ implemented | `README.md` Setup / Run / Running Tests |
| R12 | ≥3 tests | ✓ implemented | 10 `func Test*` in `main_test.go`; test_coverage=0.505 > 0 |

**requirement_coverage = 11/12 = 0.9167**

## Build & Test

Not re-run (per skill): `scores.json` → test_coverage=0.505, defect_rate=1.0, code_quality=0.956, maintainability=0.920, idiomatic=0.55. Skip count: `grep -E "t\.Skip"` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Source files | main.go (384 lines), main_test.go |
| Dependencies | modernc.org/sqlite |
| Tests total | 10 functions (+ table subtests) |
| Skipped | 0 |

## Findings

1. [high] R7 — `:memory:` SQLite: no persistence; concurrent requests 500 (`main.go:41`)
2. [medium] Tests bypass router and concurrency, hiding the R7 bug (`main_test.go`)
3. [low] Extra required fields year/isbn (`main.go:97-104`)
4. [low] 204 with JSON `null` body (`main.go:324`)
5. [low] Duplicated list query; ignored errors (`main.go:136-167`, :115, :318)

## Reproduce

```bash
grep -rn "SetMaxOpenConns\|cache=shared\|:memory:" *.go
# temp copy of main.go/go.mod/go.sum + probe_test.go firing 50 concurrent GET /books at booksHandler after initDB()
go test -v -run TestProbeConcurrent -count=1 .
```
