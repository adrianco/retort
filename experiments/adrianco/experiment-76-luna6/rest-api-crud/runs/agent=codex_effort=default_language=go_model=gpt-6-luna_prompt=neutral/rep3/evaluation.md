# Evaluation: agent=codex effort=default language=go model=gpt-6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, effort=default, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — from `defect_rate=1.0` in scores.json (build + test succeeded)
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Mechanical scores (from `scores.json`, computed inline during `retort run`): `test_coverage=0.656`, `defect_rate=1.0`, `code_quality=1.0`, `maintainability=0.806`, `idiomatic=0.67`, `token_efficiency=0.016`. `defect_rate=1.0` confirms the build and tests passed; `test_coverage=0.656` is line coverage (all 4 tests pass, 0 skips).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:44` collection POST → `book.go:39` createBook (INSERT) |
| R2 | GET /books lists all | ✓ implemented | `main.go:55` → `book.go:57` listBooks |
| R3 | GET /books ?author= filter | ✓ implemented | `book.go:60` `WHERE author = ? COLLATE NOCASE`; test `main_test.go:44` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.go:79` → `book.go:48` getBook; 404 via `ErrNotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:88` → `book.go:81` updateBook |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:101` → `book.go:97` deleteBook; 204 at `main.go:107` |
| R7 | Data stored in SQLite | ✓ implemented | `book.go:21` `sql.Open("sqlite3", dsn)`, `openDatabase` migrates table |
| R8 | JSON responses + status codes | ✓ implemented | `main.go:142` writeJSON; 201/200/204/400/404/405/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `main.go:129` blank title/author → 400; test `main_test.go:60` |
| R10 | GET /health | ✓ implemented | `main.go:18` health branch pings DB → 200/503 |
| R11 | README with setup/run | ✓ implemented | `README.md` (Run, API, Test sections) |
| R12 | ≥3 tests | ✓ implemented | 4 tests in `main_test.go`; `defect_rate=1.0`, 0 skips |

## Build & Test

Not re-run — mechanical scores were computed inline during `retort run` and stored in `scores.json`.

```text
scores.json: defect_rate=1.0  (build + go test ./... succeeded)
             test_coverage=0.656 (line coverage; 4/4 tests pass)
             code_quality=1.0
```

```text
go test funcs: TestCreateAndGetBook, TestListBooksAuthorFilter,
               TestUpdateDeleteAndValidation, TestHealthCheck
skips: 0 (grep t.Skip => 0)
```

Note: `_agent_stderr.log` shows the harness rejected an `rm -f bookapi` cleanup command during the agent's session. This did not affect the delivered code — the workspace and build are intact.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, incl. tests) | 373 (`main.go` 168, `book.go` 110, `main_test.go` 95) |
| Files (excl. .git) | 13 (incl. logs/meta; 3 Go source) |
| Dependencies (go.sum lines) | 2 (`mattn/go-sqlite3`) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Test coverage (line) | 65.6% |

## Findings

Top items (full list in `findings.jsonl` — all info-level, no defects):

1. [info] Request decoding is strict beyond spec (`DisallowUnknownFields`, 1 MiB cap) — enhancement
2. [info] Author filter is case-insensitive (`COLLATE NOCASE`) — enhancement
3. [info] PUT is a full replace requiring title+author each time — documented in README

## Reproduce

```bash
cd "experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=go_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json                                   # stored mechanical scores (no re-run)
grep -rnE "^func Test" . --include="*_test.go"    # 4 tests
grep -rcE "t\.Skip\(|t\.Skipf\(" . --include="*.go"  # 0 skips
# optional live verification:
go test ./...
```
