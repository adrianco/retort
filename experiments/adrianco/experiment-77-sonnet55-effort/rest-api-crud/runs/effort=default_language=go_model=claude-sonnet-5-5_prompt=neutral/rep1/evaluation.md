# Evaluation: effort=default_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, tooling=(none), prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list: `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — derived from stored scores (`defect_rate=1.0`, `test_coverage=0.752`) and 4 `func Test*` in `main_test.go`; not re-run
- **Build:** pass — duration not recorded (derived from `defect_rate=1.0` in `scores.json`; not re-run)
- **Lint:** pass — 0 warnings (`code_quality=1.0` in `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 2 info)

Stored scores (`scores.json`): test_coverage=0.752, code_quality=1.0, defect_rate=1.0, maintainability=0.851, idiomatic=0.83, token_efficiency=0.046.

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 entries, fixed denominator). Because a pinned list exists, no separate `P*` prompt requirements were extracted; the `neutral` prompt's only checkable ask (include tests) is covered by R12.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:20` route, `main.go:80` `create`, `store.go:50` `Store.Create` INSERT of all four fields; `main_test.go:37` `TestCRUD` expects 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:21`, `main.go:94` `list`, `store.go:60` `Store.List`; `main_test.go:76` asserts 3 books |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `main.go:95` reads `author` query, `store.go:63-66` `WHERE author = ?`; `main_test.go:77-84` `TestListAuthorFilter` (2 matches, `[]` for no match) |
| R4 | GET /books/{id} returns one book | ✓ implemented | `main.go:22`, `main.go:103` `get`, `store.go:83` `Store.Get`, 404 via `errNotFound` at `main.go:109`; `main_test.go:47`, `:99` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:23`, `main.go:119` `update`, `store.go:93` `Store.Update`; `main_test.go:52-59` verifies the change persisted |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:24`, `main.go:140` `delete`, `store.go:99` `Store.Delete`; `main_test.go:61-66` expects 204 then 404 |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite`, `store.go:26` `sql.Open("sqlite", dsn)`, `store.go:32` `CREATE TABLE IF NOT EXISTS books`; file DB `books.db` by default (`main.go:156`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `main.go:28` `writeJSON` sets `Content-Type: application/json`; 201 (`:91`), 200 (`:100`, `:116`, `:137`), 204 (`:152`), 400 (`:66`, `:83`), 404 (`:110`), 500 (`:40`); `main_test.go:87` `TestValidationAndErrors` |
| R9 | Validation: title and author required | ✓ implemented | `main.go:52-56` `decodeBook` rejects empty/whitespace title or author → 400; `main_test.go:93-96` |
| R10 | GET /health | ✓ implemented | `main.go:19`, `main.go:72` `health` returns `{"status":"ok"}` after `Store.Ping`; `main_test.go:28` `TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:6-13` "Setup & run" (`go mod download`, `go run .`, env vars), `README.md:15-17` test command |
| R12 | At least 3 unit/integration tests | ✓ implemented | `main_test.go` has 4 test functions (`:28`, `:35`, `:69`, `:87`); `test_coverage=0.752` > 0 |

Enhancements beyond spec (not deductions): `Location` header on create (`main.go:90`), health check pings the DB and returns 503 on failure (`main.go:73`), 1 MiB request-body limit (`main.go:46`), negative-year and invalid-id rejection (`main.go:57`, `main.go:65`).

## Build & Test

Not re-run — the mechanical scores were already computed by retort's scorers and are cited from `scores.json`.

```text
go build ./...
(not re-run) defect_rate=1.0 ⇒ build + tests succeeded
```

```text
go test ./...
(not re-run) test_coverage=0.752 (75.2% statement coverage), defect_rate=1.0
4 test functions: TestHealth, TestCRUD, TestListAuthorFilter, TestValidationAndErrors
0 t.Skip / t.Skipf calls
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 395 Go lines, incl. blanks/comments (`main.go` 172, `store.go` 116, `main_test.go` 107); `cloc` unavailable, `wc -l` fallback |
| Files | 17 in the archive (7 agent-authored: `main.go`, `store.go`, `main_test.go`, `go.mod`, `go.sum`, `README.md`, `.gitignore`; the rest are harness files) |
| Dependencies | 20 `go.sum` lines; 10 modules in `go.mod` (1 used directly: `modernc.org/sqlite`) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not recorded (build not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] `lint-gomod-indirect` — go.mod marks the directly imported SQLite driver as `// indirect` (`go.mod:15` vs `store.go:7`)
2. [low] `doc-go-version` — README states Go 1.22+ but go.mod requires Go 1.26.6 (`README.md:8` vs `go.mod:3`)
3. [low] `test-unchecked-unmarshal` — tests discard `json.Unmarshal` errors (`main_test.go:42`, `:56`, `:76`, `:77`)
4. [info] `coverage-main-untested` — 75.2% statement coverage; `main`/`getenv`/`serverErr` paths unexercised (`main.go:155-172`, `main.go:38-41`)
5. [info] `enh-beyond-spec` — Location header, DB-pinging health check, body limit, year/id validation

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=default_language=go_model=claude-sonnet-5-5_prompt=neutral/rep1
test -f TASK.md && test -f stack.json
cat scores.json                                   # stored mechanical scores (build/test/lint not re-run)
python3 -c "import json;[print(r) for r in json.load(open('../../../REQUIREMENTS.json'))['requirements']]"
cat -n main.go store.go main_test.go README.md go.mod
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0
grep -c '^func Test' main_test.go                  # 4
wc -l main.go store.go main_test.go                # 395
grep -c "^\s*\S" go.sum                            # 20
```
