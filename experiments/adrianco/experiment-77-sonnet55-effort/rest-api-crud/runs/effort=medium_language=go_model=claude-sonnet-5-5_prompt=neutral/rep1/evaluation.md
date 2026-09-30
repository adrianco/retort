# Evaluation: effort=medium_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, prompt=neutral, effort=medium (agent=unknown, framework=unknown; no tooling factor)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list: `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — counts derived from `main_test.go` (4 `Test*` functions) plus stored `defect_rate=1.0`; the suite was not re-run
- **Build:** pass — duration not recorded (derived from `scores.json`: `test_coverage=0.795`, `defect_rate=1.0`)
- **Lint:** pass — 0 warnings (`code_quality=1.0` from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Stored scores (`scores.json`, not re-computed): `test_coverage=0.795`, `code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.874`, `idiomatic=0.74`, `token_efficiency=0.045`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:21` route, `main.go:79` `create`, `store.go:46` `Create` inserts all four fields; `main_test.go:36` `TestCRUD` asserts 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:22`, `main.go:92` `list`, `store.go:56` `List`; `main_test.go:80` asserts 3 books, `main_test.go:72` asserts empty list is `[]` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:93` reads `author` query param, `store.go:59-62` parameterized `WHERE author = ?`; `main_test.go:81` `TestListAndAuthorFilter` asserts 2 of 3 |
| R4 | GET /books/{id} returns one book | ✓ implemented | `main.go:23`, `main.go:101` `get`, `store.go:79` `Get` maps `sql.ErrNoRows` → 404; `main_test.go:46`, `main_test.go:100` (404) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:24`, `main.go:114` `update`, `store.go:89` `Update`; `main_test.go:51-57` asserts update is persisted, `main_test.go:98` (404 on missing) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:25`, `main.go:131` `delete`, `store.go:95` `Delete`; `main_test.go:59-67` asserts 204, then 404 on get and on repeat delete |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite` driver, `store.go:25` `sql.Open("sqlite", dsn)`, schema at `store.go:30`; file-backed `books.db` by default (`main.go:144-147`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `main.go:29` `writeJSON` sets `Content-Type: application/json`; 201 (`main.go:89`), 200, 204 (`main.go:140`), 400 (`main.go:53`), 404 (`main.go:41`), 500 (`main.go:45`); codes asserted throughout `main_test.go` |
| R9 | Validation: title and author required | ✓ implemented | `main.go:57-61` rejects empty/whitespace title or author with 400, shared by create and update; `main_test.go:93-94`, `main_test.go:97` |
| R10 | GET /health | ✓ implemented | `main.go:18-20` returns `{"status":"ok"}` 200; `main_test.go:28` `TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:5-13` Run (`go run .`, `ADDR`/`DB_PATH` env) and Test sections; `README.md:3` notes no CGO needed; endpoint table `README.md:15-24` |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 test functions in `main_test.go` (`TestHealth`, `TestCRUD`, `TestListAndAuthorFilter`, `TestValidation`); `test_coverage=0.795` > 0 |

Prompt factor `prompts/neutral.md` prescribes no methodology and asks only for tests that demonstrate the requirements — satisfied by R12's evidence. The pinned list is the complete checklist, so no `P*` rows are scored.

Enhancements beyond spec: 1 MiB request-body cap (`main.go:50`), `Location` header on create (`main.go:88`), negative-year rejection (`main.go:62`), id validation with 400 (`main.go:72`).

## Build & Test

Not re-run — the skill forbids re-running the toolchain when stored scores exist.

```text
go build ./...
(not executed; defect_rate=1.0 from scores.json ⇒ build + tests succeeded)
```

```text
go test ./...
(not executed; test_coverage=0.795 from scores.json ⇒ tests ran, 79.5% statement coverage)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 374 Go lines (267 non-test in `main.go` + `store.go`, 107 in `main_test.go`) |
| Files | 7 agent-produced (`main.go`, `store.go`, `main_test.go`, `go.mod`, `go.sum`, `README.md`, `TASK.md`) |
| Dependencies | 20 `go.sum` lines; 10 modules in `go.mod` (1 direct: `modernc.org/sqlite`) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not recorded |

## Findings

Top by severity (full list in `findings.jsonl`):

1. [low] `go.mod:15` marks the directly imported `modernc.org/sqlite` as `// indirect` — `go mod tidy` was not run after adding the import.
2. [info] Tests discard `json.Unmarshal` errors (`main_test.go:41`, `main_test.go:80-81`).
3. [info] Beyond-spec hardening: body cap, `Location` header, negative-year and id validation.

## Reproduce

```bash
cd "experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=medium_language=go_model=claude-sonnet-5-5_prompt=neutral/rep1"
cat stack.json scores.json _meta.json
cat ../../../REQUIREMENTS.json ../../../prompts/neutral.md
cat -n TASK.md main.go store.go main_test.go README.md go.mod
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0
grep -c "^func Test" main_test.go                              # 4
grep -c "^\s*\S" go.sum                                        # 20
wc -l *.go                                                     # 374 total
```
