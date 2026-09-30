# Evaluation: effort=low_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, prompt=neutral, effort=low (agent=unknown, framework=unknown; no tooling factor)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list: `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — derived from stored scores, not re-run
- **Build:** pass — duration not measured (not re-run; `defect_rate=1.0`, `test_coverage=0.779` from `scores.json`)
- **Lint:** pass — 0 warnings (`code_quality=1.0` from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:21` route, `main.go:72-84` `create`, `store.go:47-55` `Store.Create` inserts all four fields; `main_test.go:37` `TestCRUD` asserts 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:22`, `main.go:86-93` `list`, `store.go:57-78` `Store.List`; `main_test.go:95` `TestListFilter` asserts 3 rows |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `main.go:87` passes the query param, `store.go:60-63` adds `WHERE author = ?`; `main_test.go:96-103` asserts 2 of 3 and `[]` for no match |
| R4 | GET /books/{id} returns one book | ✓ implemented | `main.go:23`, `main.go:95-107` `get`, `store.go:80-88` maps `sql.ErrNoRows` to `errNotFound` → 404; `main_test.go:47,60` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:24`, `main.go:109-126` `update`, `store.go:90-100`; `main_test.go:52` asserts 200 + new title, `:66` asserts 404 on missing |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:25`, `main.go:128-139` `delete`, `store.go:102-111`; `main_test.go:57-65` asserts 204, then 404 on get and on second delete |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite`, `store.go:26` `sql.Open("sqlite", dsn)`, schema at `store.go:31-37`; file-backed `books.db` by default (`main.go:142-145`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `main.go:29-33` `writeJSON` sets `Content-Type: application/json`; 201 (`:83`), 200, 204 (`:138`), 400 (`:75`), 404 (`:41`), 500 (`:45`); codes asserted throughout `main_test.go` |
| R9 | Validation: title and author required | ✓ implemented | `main.go:54-60` trims and rejects empty title/author with 400; `main_test.go:71-86` `TestValidation` covers missing title, missing author, blank title, on both POST and PUT |
| R10 | GET /health | ✓ implemented | `main.go:18-20` returns 200 `{"status":"ok"}`; `main_test.go:28-33` `TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:5-13` (`go run .`, env vars `ADDR`/`DB_PATH`, `go test ./...`), endpoint table `README.md:15-24` |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 test functions in `main_test.go` (`TestHealth`, `TestCRUD`, `TestValidation`, `TestListFilter`); `test_coverage=0.779` > 0 so they ran |

Enhancements beyond spec (not deductions): `Location` header on create (`main.go:82`), negative-year rejection (`main.go:61-62`), id validation → 400 (`main.go:67-70`), 1 MiB body cap (`main.go:50`).

## Build & Test

Build, tests and lint were **not re-run** — per the skill, the stored scores stand in for them.

```text
cat scores.json
{"code_quality": 1.0, "token_efficiency": 0.04379831666710641, "test_coverage": 0.779, "defect_rate": 1.0, "maintainability": 0.8710105164870913, "idiomatic": 0.8}
```

```text
grep -c "^func Test" main_test.go      -> 4
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   -> 0
```

`test_coverage=0.779` is statement coverage from a passing `go test` run (`defect_rate=1.0` ⇒ build + tests succeeded); the per-test pass count of 4 is inferred from that, not observed directly.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 372 (main.go 157, store.go 111, main_test.go 104) |
| Files | 6 generated (main.go, store.go, main_test.go, go.mod, go.sum, README.md); 13 in the archive incl. TASK.md, stack.json and harness `_*` files |
| Dependencies | 10 modules in go.mod (1 direct: modernc.org/sqlite); 20 go.sum lines |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not measured (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] go.mod marks the directly imported `modernc.org/sqlite` as `// indirect` (`go.mod:15` vs `store.go:7`) — `go mod tidy` was not run
2. [low] Tests discard `json.Unmarshal` errors (`main_test.go:42`, `:95-96`)
3. [info] Oversized request body reported as 400 "invalid JSON body" rather than 413 (`main.go:50-53`)
4. [info] Enhancements beyond spec: Location header, year validation, id validation, body cap

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=low_language=go_model=claude-sonnet-5-5_prompt=neutral/rep3
cat stack.json scores.json
cat ../../../REQUIREMENTS.json
grep -c "^func Test" main_test.go
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
wc -l main.go store.go main_test.go
grep -c "^\s*\S" go.sum
```
