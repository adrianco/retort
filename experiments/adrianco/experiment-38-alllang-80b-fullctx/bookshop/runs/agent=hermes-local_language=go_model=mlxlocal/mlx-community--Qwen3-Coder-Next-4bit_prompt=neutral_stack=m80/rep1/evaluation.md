# Evaluation: go · hermes-local · Qwen3-Coder-Next-4bit (m80) · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass (code_quality=1.0 from scores.json) — 0 warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low)

All 12 pinned requirements (`REQUIREMENTS.json`) are met. The build passes, all 11 tests
pass with no skips, and lint is clean. One genuine (untested) edge-case defect: PUT to a
non-existent id returns 500 instead of 404 because `UpdateBook` returns a plain error while
the handler checks `sql.ErrNoRows`. Two low-severity nits (dependency pin, fragile test id
construction). None are high-severity, so this run passes the conformance gate.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:155` createBookHandler → `database.go:61` CreateBook (201) |
| R2 | GET /books lists all | ✓ implemented | `main.go:131` listBooksHandler → `database.go:9` GetBooks |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:139` branch → `database.go:29` GetBooksByAuthor (LIKE) |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.go:180` getBookHandler; `sql.ErrNoRows`→404 at `main.go:194` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:207` updateBookHandler → `database.go:85` UpdateBook (missing-id → 500, see findings) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:245` deleteBookHandler → `database.go:108` DeleteBook (204; 404 if absent) |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:15,59` mattn/go-sqlite3; `books` table `main.go:65` |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/204/400/404 across handlers; JSON Content-Type set |
| R9 | Validation: title & author required | ✓ implemented | `main.go:84` BookInput.Validate; tested `main_test.go:84` TestCreateBookValidation |
| R10 | GET /health | ✓ implemented | `main.go:121` healthHandler; tested `main_test.go:28` |
| R11 | README with setup/run | ✓ implemented | `README.md` — install, run, endpoints, testing |
| R12 | ≥3 tests | ✓ implemented | 11 test funcs in `main_test.go`; test_coverage=0.695 |

## Build & Test

Not re-run — scores read from `scores.json` (inline eval gate):

```text
defect_rate    = 1.0    → go build + go test succeeded
test_coverage  = 0.695  → tests executed; 69.5% statement coverage
code_quality   = 1.0    → lint clean
```

Agent's own report (`_agent_stdout.log`): "All 11 tests pass … binary builds successfully."
No `t.Skip` calls present.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 421 (main.go 299, database.go 122) |
| Test LOC | 396 |
| Files | 14 (incl. build/meta) |
| Dependencies (go.sum lines) | 14 |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Statement coverage | 69.5% |

## Findings

Top items (full list in `findings.jsonl`):

1. [medium] PUT /books/{id} on a non-existent id returns 500 instead of 404 — `main.go:232` vs `database.go:93`
2. [low] mattn/go-sqlite3 pinned to mis-tagged v2.0.3+incompatible — `go.mod:6`
3. [low] Test URL construction only works for single-digit ids — `main_test.go:158`

## Reproduce

```bash
cd <run_dir>
cat scores.json                 # stored build/test/lint scores (not re-run)
grep -rEc "t\.Skip" . --include="*.go"   # → 0 skips
grep -c "^func Test" main_test.go        # → 11 tests
# Optional live verify:
go test -v -cover ./...
```
