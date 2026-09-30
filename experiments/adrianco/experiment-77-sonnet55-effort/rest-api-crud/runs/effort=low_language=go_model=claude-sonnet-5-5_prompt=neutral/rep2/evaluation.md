# Evaluation: effort=low_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, effort=low, prompt=neutral (agent=unknown, framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list: `../../../REQUIREMENTS.json`)
- **Tests:** 4 defined / 0 skipped (4 effective) — not re-run; stored `test_coverage=0.779`, `defect_rate=1.0` from `scores.json` ⇒ build + tests passed
- **Build:** pass (derived from `defect_rate=1.0` in `scores.json`; duration not recorded)
- **Lint:** pass — `code_quality=1.0` from `scores.json`; 2 low-severity warnings found by reading the code
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:20` route, `main.go:76` `create`, `store.go:43` `Store.Create` inserts all four fields; `main_test.go:36` `TestCRUD` expects 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:21`, `main.go:88` `list`, `store.go:52` `Store.List`; `main_test.go:83` `TestListAuthorFilter` (`len(all) == 2`) |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `main.go:89` reads `author` query param, `store.go:55-58` `WHERE author = ?`; `main_test.go:84` |
| R4 | GET /books/{id} returns one book | ✓ implemented | `main.go:22`, `main.go:97` `get`, `store.go:75` `Store.Get` → `ErrNotFound` → 404 (`main.go:39`); `main_test.go:45,55` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:23`, `main.go:110` `update`, `store.go:85` `Store.Update` (404 on 0 rows); `main_test.go:48,58` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:24`, `main.go:127` `delete`, `store.go:96` `Store.Delete`; `main_test.go:52,61` |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite`, `store.go:23` `sql.Open("sqlite", dsn)`, `store.go:28` `CREATE TABLE IF NOT EXISTS books`; file-backed `books.db` by default (`main.go:142`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `main.go:28` `writeJSON` sets `Content-Type: application/json`; 201 (`main.go:85`), 200, 204 (`main.go:136`), 400 (`main.go:50-60,70`), 404 (`main.go:40`), 500 (`main.go:44`); asserted throughout `main_test.go` |
| R9 | Validation: title and author required | ✓ implemented | `main.go:53-58` trims then rejects empty title/author with 400; `main_test.go:66` `TestValidation` |
| R10 | GET /health | ✓ implemented | `main.go:17` returns `{"status":"ok"}` 200; `main_test.go:28` `TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:5-10` — `go run .`, env vars `ADDR`/`DB_PATH`, `go test ./...`; endpoint list at `README.md:12-18` |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 tests in `main_test.go` (`TestHealth`, `TestCRUD`, `TestValidation`, `TestListAuthorFilter`); `test_coverage=0.779 > 0` |

Enhancements beyond spec (not deductions): 1 MiB request-body cap (`main.go:49`), whitespace-trimmed validation (`main.go:53`), negative-year rejection (`main.go:59`), 400 on non-numeric id (`main.go:70`), env-configurable `ADDR`/`DB_PATH`, CGO-free SQLite driver.

## Build & Test

Not re-run — the skill forbids re-running the toolchain when stored scores exist.

```text
scores.json
{"code_quality": 1.0, "token_efficiency": 0.041992441360555105, "test_coverage": 0.779,
 "defect_rate": 1.0, "maintainability": 0.8408673549409736, "idiomatic": 0.81}
```

```text
go test ./...   (not executed here)
test_coverage=0.779  → tests executed and passed, 77.9% statement coverage
defect_rate=1.0      → build + test succeeded
skips: grep -rE "t\.Skip\(|t\.Skipf\(" --include="*.go"  → 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 260 (`main.go` 155 + `store.go` 105); tests 88 |
| Files | 7 agent-produced (`main.go`, `store.go`, `main_test.go`, `go.mod`, `go.sum`, `README.md`, `TASK.md`) |
| Dependencies | 1 direct (`modernc.org/sqlite`), 10 modules in `go.mod`, 20 `go.sum` lines |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not recorded |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] `go.mod:14` marks the directly-imported `modernc.org/sqlite` as `// indirect` — `go mod tidy` was not run.
2. [low] Tests discard `json.Unmarshal` errors (`main_test.go:41,83,84`).
3. [info] PUT validation and the `year < 0` rule are not exercised by any test (`main_test.go:66-76`).
4. [info] PUT is a full replace — omitted `year`/`isbn` reset to zero values (`main.go:115-120`, `store.go:86`).
5. [info] Enhancements beyond spec (body cap, trimmed validation, env config, CGO-free driver).

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=low_language=go_model=claude-sonnet-5-5_prompt=neutral/rep2
cat scores.json
cat ../../../REQUIREMENTS.json
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
wc -l *.go
grep -c "^\s*\S" go.sum
```
