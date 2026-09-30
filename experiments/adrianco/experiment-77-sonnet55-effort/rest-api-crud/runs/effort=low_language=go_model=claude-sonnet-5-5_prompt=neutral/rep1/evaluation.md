# Evaluation: effort=low_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, prompt=neutral, effort=low (agent=unknown, framework=unknown; no tooling factor)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list: `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — derived from stored scores, not re-run
- **Build:** pass — duration not measured (derived from `defect_rate=1.0` in `scores.json`)
- **Lint:** pass — 0 warnings from the scorer (`code_quality=1.0` in `scores.json`); 2 low-severity review notes
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:22` route, `main.go:80` `create`, `store.go:44` `Store.Create` inserts all four fields; `main_test.go:37` `TestCRUD` asserts 201 + body |
| R2 | GET /books lists all books | ✓ implemented | `main.go:23`, `main.go:92` `list`, `store.go:54` `Store.List`; `main_test.go:89` asserts 3 of 3 returned |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `main.go:93` reads `author` query param, `store.go:57-59` `WHERE author = ?`; `main_test.go:90` `TestListAuthorFilter` asserts 2 of 3 |
| R4 | GET /books/{id} returns one book | ✓ implemented | `main.go:24`, `main.go:101` `get`, `store.go:77` `Store.Get`; `sql.ErrNoRows` → 404 at `main.go:72`; `main_test.go:47,57` assert 200 then 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:25`, `main.go:114` `update`, `store.go:88` `Store.Update`; `main_test.go:50` asserts 200 + new title, `main_test.go:63` asserts 404 on missing |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:26`, `main.go:131` `delete`, `store.go:95` `Store.Delete`; `main_test.go:54,60` assert 204 then 404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:6` `modernc.org/sqlite` driver, `store.go:23` `sql.Open("sqlite", dsn)`, `store.go:28` `CREATE TABLE IF NOT EXISTS books`; file-backed `books.db` by default (`main.go:146`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `main.go:30` `writeJSON` sets `Content-Type: application/json`; 201 (`main.go:89`), 200, 204 (`main.go:140`), 400 (`main.go:44-55,65`), 404 (`main.go:73`), 500 (`main.go:77`); codes asserted throughout `main_test.go` |
| R9 | Validation: title and author required | ✓ implemented | `main.go:50-53` return 400 for empty title/author after trimming; `main_test.go:70` `TestValidation` covers missing title, missing author, blank title |
| R10 | GET /health health check | ✓ implemented | `main.go:19-21` returns 200 `{"status":"ok"}`; `main_test.go:28` `TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:5-9` run command + `ADDR`/`DB_PATH` env vars, `README.md:11-13` test command, `README.md:15-24` endpoint table |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 test functions in `main_test.go` (`TestHealth`, `TestCRUD`, `TestValidation`, `TestListAuthorFilter`); `test_coverage=0.788` in `scores.json` shows they executed |

Enhancements beyond spec (not deductions): 1 MiB request-body cap (`main.go:41`), whitespace-trimmed
title/author (`main.go:47-48`), negative-year rejection (`main.go:54`), 400 on malformed id
(`main.go:64`), empty list serialised as `[]` rather than `null` (`store.go:66`).

## Build & Test

Build, tests and lint were **not re-run** — the stored scores from `scores.json` stand in for them,
as the skill requires.

```text
cat scores.json
{"code_quality": 1.0, "token_efficiency": 0.0427, "test_coverage": 0.788,
 "defect_rate": 1.0, "maintainability": 0.8468, "idiomatic": 0.88}
```

```text
go test ./...   (not re-run; interpreted from stored scores)
test_coverage = 0.788  -> tests executed, 78.8% statement coverage
defect_rate   = 1.0    -> build + tests succeeded
code_quality  = 1.0    -> lint clean
```

The pass count of 4 is the number of `Test*` functions in `main_test.go` combined with
`defect_rate=1.0`; no per-test output was captured in this evaluation.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 267 (`main.go` 159, `store.go` 108); tests 94 |
| Files | 18 (incl. harness logs, `scores.json`, `summary/`; excl. `_judge/`) |
| Dependencies | 1 direct (`modernc.org/sqlite`), 10 modules in `go.mod`, 20 `go.sum` lines |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | not measured (build not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] `go.mod:15` marks the directly imported `modernc.org/sqlite` as `// indirect` — `go mod tidy` was not run.
2. [low] Tests ignore `json.Unmarshal` errors (`main_test.go:42,89,90`).
3. [info] Validation and hardening beyond spec (body cap, trimming, year and id checks, `[]` for empty list).

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=low_language=go_model=claude-sonnet-5-5_prompt=neutral/rep1
cat stack.json scores.json _meta.json
cat ../../../REQUIREMENTS.json            # pinned 12-item checklist
cat TASK.md main.go store.go main_test.go README.md go.mod
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0
wc -l main.go store.go main_test.go
grep -c "^\s*\S" go.sum                   # 20
find . -type f -not -path "./_judge/*" | wc -l
```
