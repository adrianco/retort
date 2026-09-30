# Evaluation: effort=medium_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, effort=medium, prompt=neutral (agent=unknown, framework=unknown; no tooling factor)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `REQUIREMENTS.json`)
- **Tests:** 4 test functions, all passing / 0 failed / 0 skipped (4 effective) — derived from stored `defect_rate=1.0`; not re-run
- **Build:** pass — duration not recorded (derived from `scores.json`: `defect_rate=1.0`, `test_coverage=0.809`)
- **Lint:** pass — 0 warnings from the scorer (`code_quality=1.0`); 2 low-severity items found by reading the code
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `handlers.go:17`, `handlers.go:83` `create` → `store.go:48` `Store.Create` inserts all four fields; `main_test.go:37` `TestCRUD` asserts 201 + body |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:18`, `handlers.go:97` `list` → `store.go:58` `Store.List`; `main_test.go:99` asserts 3 books, `main_test.go:91` asserts `[]` when empty |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `handlers.go:98` reads `author` query param; `store.go:61-63` `WHERE author = ?`; `main_test.go:100` `TestListAuthorFilter` asserts 2 of 3 |
| R4 | GET /books/{id} returns one book | ✓ implemented | `handlers.go:19`, `handlers.go:106` `get` → `store.go:81` `Store.Get` (`sql.ErrNoRows` → 404); `main_test.go:47`, `main_test.go:60` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:20`, `handlers.go:119` `update` → `store.go:91` `Store.Update`; `main_test.go:52` (200), `main_test.go:66` (404 on missing) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:21`, `handlers.go:136` `delete` → `store.go:97` `Store.Delete`; `main_test.go:57` (204), `main_test.go:63` (404 on missing) |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite`, `store.go:26` `sql.Open("sqlite", dsn)`, `store.go:32` `CREATE TABLE IF NOT EXISTS books`; `main.go:17` defaults to file `books.db` (tests use `:memory:`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `handlers.go:27` `writeJSON` sets `Content-Type: application/json`; 201 (`handlers.go:94`), 200, 204 (`handlers.go:145`), 400 (`handlers.go:49`, `60`, `68`), 404 (`handlers.go:39`), 500 (`handlers.go:43`); codes asserted throughout `main_test.go` |
| R9 | Validation: title and author required | ✓ implemented | `handlers.go:67-70` rejects empty/whitespace title or author with 400; `main_test.go:71` `TestValidation` covers missing title, missing author, blank title, on both POST and PUT |
| R10 | GET /health endpoint | ✓ implemented | `handlers.go:16`, `handlers.go:79` returns 200 `{"status":"ok"}`; `main_test.go:28` `TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:6-10` run (`go run .`, `ADDR`, `DB_PATH`), `README.md:12-14` test, endpoint table `README.md:18-25` |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 test functions in `main_test.go` (`TestHealth`, `TestCRUD`, `TestValidation`, `TestListAuthorFilter`); `test_coverage=0.809 > 0` |

Pinned `REQUIREMENTS.json` is the complete checklist, so no separate `P*` prompt requirements were extracted. (`prompts/neutral.md` only asks for tests that demonstrate the requirements — satisfied by R12.)

Enhancements beyond spec (not deductions): 1 MiB request-body cap, negative-year validation, 400 on malformed ids, `Location` header on create.

## Build & Test

Build, tests and lint were **not re-run** — the scores retort stored for this run are used, as the skill requires.

```text
scores.json
{"code_quality": 1.0, "token_efficiency": 0.0452, "test_coverage": 0.809,
 "defect_rate": 1.0, "maintainability": 0.8153, "idiomatic": 0.7}
```

```text
defect_rate=1.0      -> build + tests succeeded
test_coverage=0.809  -> tests executed; 80.9% coverage
code_quality=1.0     -> lint clean
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go"  -> 0 skips
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 285 non-test Go (main.go 25, store.go 114, handlers.go 146) + 104 test = 389 (`wc -l`; `cloc` unavailable) |
| Files | 15 (excluding `summary/`, `_judge/`) |
| Dependencies | 20 `go.sum` lines; 10 modules in `go.mod` (1 direct: `modernc.org/sqlite`) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not recorded |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] `go.mod:14` marks the directly imported `modernc.org/sqlite` as `// indirect` — needs `go mod tidy`
2. [low] JSON encode/decode errors discarded — `handlers.go:30`, `main_test.go:42`, `99`, `100`
3. [info] PUT is a full replacement; omitted `year`/`isbn` reset to zero values (`handlers.go:124-129`, documented in README)
4. [info] Health check does not probe the database (`handlers.go:79-81`)
5. [info] Enhancements beyond spec: body cap, negative-year and id validation, `Location` header

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=medium_language=go_model=claude-sonnet-5-5_prompt=neutral/rep2
cat scores.json
cat ../../../REQUIREMENTS.json
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
grep -cE "^func Test" main_test.go
wc -l main.go store.go handlers.go main_test.go
grep -c "^\s*\S" go.sum
# optional, not run here: go test -cover ./...
```
