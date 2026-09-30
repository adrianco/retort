# Evaluation: effort=high_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, effort=high, prompt=neutral (agent/framework recorded as `unknown` in `stack.json`; no tooling factor)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, fixed denominator 12)
- **Tests:** 8 test functions (16 incl. the 8 `TestValidation` subtests) passed / 0 failed / 0 skipped (8 effective) — pass state taken from `scores.json`, not re-run
- **Build:** pass — duration not measured (derived from `defect_rate=1.0`, `test_coverage=0.747` in `scores.json`; toolchain not re-run per skill)
- **Lint:** pass — 0 warnings (`code_quality=1.0` from `scores.json`); one manual go.mod hygiene note below
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

Stored scores (`scores.json`): test_coverage=0.747, code_quality=1.0, defect_rate=1.0, maintainability=0.891, idiomatic=0.87, token_efficiency=0.037.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `handlers.go:24` route, `handlers.go:103` `createBook`, `store.go:54` `Create` INSERTs all four fields; `handlers_test.go:55` `TestCreateAndGet` |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:25`, `handlers.go:117` `listBooks`, `store.go:65` `List`; `handlers_test.go:116` asserts 3 of 3 returned, `:104` empty list is `[]` |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `handlers.go:118` passes `author` query param, `store.go:68-70` `WHERE author = ?` (exact match); `handlers_test.go:119` `TestListAndAuthorFilter` |
| R4 | GET /books/{id} returns one book | ✓ implemented | `handlers.go:26`, `handlers.go:126` `getBook`, 404 via `ErrNotFound` at `handlers.go:132`; `handlers_test.go:67`, `:158` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:27`, `handlers.go:142` `updateBook`, `store.go:99` `Update`; `handlers_test.go:130` `TestUpdate` (checks persisted value and 404) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:28`, `handlers.go:163` `deleteBook`, `store.go:113` `Delete`; `handlers_test.go:147` `TestDelete` |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite`, `store.go:29` `sql.Open("sqlite", dsn)`, file-backed `books.db` (`main.go:19`); `handlers_test.go:168` `TestPersistsAcrossReopen` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `handlers.go:32` `writeJSON` sets `Content-Type: application/json`; 201 (`:114`), 200, 204 (`:175`), 400 (`:64`, `:89`), 404, 422 (`:75`), 500 (`:46`), 503 (`:97`); statuses asserted throughout `handlers_test.go` |
| R9 | Validation: title and author required | ✓ implemented | `handlers.go:73-77` rejects blank/missing title or author on both POST and PUT; `handlers_test.go:74` `TestValidation`. Note: rejection status is 422, not the 400 the pinned `how_to_verify` mentions — still a correct client-error rejection |
| R10 | GET /health endpoint | ✓ implemented | `handlers.go:23`, `handlers.go:95` `health` (pings DB, 200 `{"status":"ok"}`); `handlers_test.go:46` `TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:7-14` build/run, `:16-21` config, `:23-27` test, `:29-38` endpoints |
| R12 | At least 3 unit/integration tests | ✓ implemented | 8 `Test*` functions in `handlers_test.go`; `test_coverage=0.747` (> 0) |

No `P*` list: the pinned `REQUIREMENTS.json` is the complete checklist. (The `neutral` prompt only asks for tests demonstrating the requirements, which R12 covers.)

## Build & Test

Not re-run — scores read from `scores.json` as the skill requires.

```text
go build ./...        # not re-run; defect_rate=1.0 ⇒ build + tests succeeded
```

```text
go test ./...         # not re-run; test_coverage=0.747 (statement coverage, tests executed and passed)
8 test functions, 0 t.Skip/t.Skipf
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 335 (`main.go` 35, `handlers.go` 176, `store.go` 124); tests 188 — `wc -l`, `cloc` not installed |
| Files | 8 deliverable files (4 `.go`, `go.mod`, `go.sum`, `README.md`, `.gitignore`); 22 in the archive incl. harness logs, `_judge/`, `summary/` |
| Dependencies | 20 `go.sum` lines; 1 direct module (`modernc.org/sqlite`) + 9 transitive in `go.mod` |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | not measured (toolchain not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Direct dependency `modernc.org/sqlite` is marked `// indirect` — `go.mod:15` vs `store.go:7`; `go mod tidy` was not run.
2. [low] README says Go 1.22+ but `go.mod` requires 1.26.6 — `README.md:9` vs `go.mod:3`.
3. [info] Hardening beyond spec — Location header, 1 MiB body cap, unknown-field rejection, year validation, DB-backed health check, reopen-persistence test.

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=high_language=go_model=claude-sonnet-5-5_prompt=neutral/rep3
cat scores.json
cat ../../../REQUIREMENTS.json
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
grep -c "^func Test" handlers_test.go
wc -l *.go
grep -c "^\s*\S" go.sum
```
