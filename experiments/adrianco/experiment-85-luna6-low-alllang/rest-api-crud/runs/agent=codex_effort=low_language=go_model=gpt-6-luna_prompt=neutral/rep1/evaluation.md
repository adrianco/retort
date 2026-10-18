# Evaluation: rest-api-crud · agent=codex effort=low language=go model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=unknown (stdlib `net/http`)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json` R1–R12)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — `test_coverage=0.6` from scores.json (tests executed), `defect_rate=1.0` (build + tests succeeded)
- **Build:** pass — not re-run (stored `defect_rate=1.0`)
- **Lint:** pass — `code_quality=0.9556` from scores.json; 1 low-severity dead-code note
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low)

The `prompt=neutral` factor (`prompts/neutral.md`) prescribes no methodology and adds no checkable requirements beyond "include tests", which R12 already covers — so there are no `P*` requirements.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:90 createBook` INSERTs all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:108 listBooks` SELECTs all, returns `[]Book` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:111` `WHERE author = ?` when query param present |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:137 getBook`; 404 on `sql.ErrNoRows` (`main.go:139`) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:150 updateBook` UPDATE; 404 when RowsAffected==0 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:173 deleteBook` DELETE; 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:28 openDB` opens `modernc.org/sqlite`, creates `books` table |
| R8 | JSON responses + correct status codes | ✓ implemented | `writeJSON`/`writeError` (`main.go:221`); 201/200/204/400/404/405 used |
| R9 | Validation: title and author required | ✓ implemented | `main.go:214 decodeBook` rejects empty title/author with 400; tested `main_test.go:72` |
| R10 | GET /health endpoint | ✓ implemented | `main.go:50` returns 200 `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` documents `go run .`, env vars, endpoints, `go test ./...` |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 3 test funcs in `main_test.go`; `test_coverage=0.6 > 0` |

## Build & Test

Not re-run — stored scores used per the evaluate-run skill (compiled language; re-running the toolchain is pure duplication).

```text
scores.json
test_coverage = 0.6     (tests executed; coverage fraction)
defect_rate   = 1.0     (build + tests succeeded)
code_quality  = 0.9556
maintainability = 0.9270
idiomatic     = 0.6
token_efficiency = 0.0254
```

```text
go test ./...   (3 tests, from main_test.go)
TestCreateGetAndListBooks   — POST + GET/{id} + ?author= list
TestValidationAndNotFound   — 400 on blank title, 404 on missing id
TestUpdateDeleteAndHealth   — PUT, DELETE (204), GET /health
skips: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 355 (main.go 255 + main_test.go 100) |
| Files | 12 (incl. go.mod/go.sum/README) |
| Dependencies | 1 direct (`modernc.org/sqlite`), 9 indirect |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Unused `API.ping` readiness helper is dead code — `main.go:255`

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=go_model=gpt-6-luna_prompt=neutral/rep1"
cat scores.json
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
grep -rE "^func Test" main_test.go
# optional direct verification:
go test ./...
```
