# Evaluation: effort=default_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, prompt=neutral, effort=default (agent=unknown, framework=unknown; no tooling factor)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list: `REQUIREMENTS.json`, R1–R12)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — 5 `Test*` functions in `main_test.go`; pass status taken from `scores.json` (`defect_rate=1.0`, `test_coverage=0.805`), not re-run
- **Build:** pass — duration n/a (not re-run; `defect_rate=1.0` from `scores.json`)
- **Lint:** pass — 0 warnings from the scorer (`code_quality=1.0` from `scores.json`); 2 low-severity review notes in findings
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:21` route, `main.go:79` `create`, `store.go:48` `Create` INSERT of all four fields; `main_test.go:37` `TestCRUDLifecycle` asserts 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:22`, `main.go:92` `list`, `store.go:69` `List`; `main_test.go:83` asserts 3 books |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `main.go:93` reads `author` query param, `store.go:72-75` `WHERE author = ?`; `main_test.go:84-91` `TestListAndAuthorFilter` (2 of 3, and `[]` for no match) |
| R4 | GET /books/{id} returns one book | ✓ implemented | `main.go:23`, `main.go:101` `get`, `store.go:58` `Get` → `errNotFound` → 404 (`main.go:40`); `main_test.go:47`, `main_test.go:96` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:24`, `main.go:114` `update`, `store.go:92` `Update` (404 when 0 rows affected); `main_test.go:50`, `main_test.go:99` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:25`, `main.go:131` `delete`, `store.go:104` `Delete`; `main_test.go:54-58` asserts 204 then 404 on re-GET |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite`, `store.go:26` `sql.Open("sqlite", dsn)`, `store.go:32` `CREATE TABLE IF NOT EXISTS books`; file-backed `books.db` by default (`main.go:151`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `main.go:29` `writeJSON` sets `Content-Type: application/json`; 201 (`main.go:89`), 200, 204 (`main.go:140`), 400 (`main.go:53-63`, `main.go:73`), 404 (`main.go:41`), 500 (`main.go:45`); asserted throughout `main_test.go` |
| R9 | Validation: title and author required | ✓ implemented | `main.go:58-61` → 400 after `TrimSpace`; `main_test.go:62` `TestValidation` covers missing title, missing author, blank title, on both POST and PUT |
| R10 | GET /health | ✓ implemented | `main.go:18-20` returns 200 `{"status":"ok"}`; `main_test.go:28` `TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:5-13` Run (`go run .`, `ADDR`/`DB_PATH` env) and Test sections; `README.md:15-30` endpoint table and curl example |
| R12 | At least 3 unit/integration tests | ✓ implemented | 5 tests in `main_test.go` (lines 28, 35, 62, 76, 94); `test_coverage=0.805` (> 0 ⇒ tests executed) |

Enhancements beyond spec (not deductions): 1 MiB request-body cap (`main.go:51`), `Location` header on create (`main.go:88`), negative-year rejection (`main.go:62`), bad-id → 400 (`main.go:72`), env-configurable `ADDR`/`DB_PATH` (`main.go:151,156`).

## Build & Test

Not re-run — scores read from `scores.json` per the skill (mechanical scorers already ran the toolchain).

```text
scores.json
{"code_quality": 1.0, "token_efficiency": 0.04517880483962864, "test_coverage": 0.805, "defect_rate": 1.0, "maintainability": 0.8826573473482974, "idiomatic": 0.75}
```

```text
go test ./...   (not re-run)
defect_rate=1.0  ⇒ build + tests succeeded
test_coverage=0.805 ⇒ tests executed, 80.5% statement coverage
t.Skip / t.Skipf occurrences: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 272 (`main.go` 159 + `store.go` 113); tests 108 |
| Files | 20 at evaluation time (3 `.go`, `go.mod`, `go.sum`, README, TASK, plus harness logs/metadata and `summary/`) |
| Dependencies | 1 direct (`modernc.org/sqlite`), 10 modules in `go.mod`, 20 `go.sum` lines |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top by severity (full list in `findings.jsonl`):

1. [low] `lint-gomod-indirect` — `modernc.org/sqlite` is imported directly (`store.go:7`) but marked `// indirect` in `go.mod:15`; `go mod tidy` was not run.
2. [low] `test-unchecked-unmarshal` — `main_test.go:42,83,84` discard `json.Unmarshal` errors; list test never asserts the 200 status.
3. [info] `enh-hardening` — enhancements beyond spec (body cap, Location header, extra validation, env config).

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=default_language=go_model=claude-sonnet-5-5_prompt=neutral/rep3
cat scores.json stack.json _meta.json
cat ../../../REQUIREMENTS.json
cat -n main.go store.go main_test.go README.md go.mod
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
grep -c "^func Test" main_test.go
wc -l main.go store.go main_test.go
grep -c "^\s*\S" go.sum
```
