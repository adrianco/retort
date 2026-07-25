# Evaluation: agent=hermes-local language=go model=gpt-oss-20b prompt=neutral stack=gptoss · rep 2

## Summary

- **Factors:** language=go, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (R8 implemented with a low caveat on error-body format)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass (test_coverage=0.596 from scores.json ⇒ build+tests ran and passed)
- **Lint:** pass — code_quality=0.9556 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:70` handleCreate — decodes title/author/year/isbn, INSERTs, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `main.go:93` handleList — SELECT all, returns JSON array |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:97` WHERE author=? branch; tested `book_test.go:96` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.go:121` handleGet — sql.ErrNoRows → 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:139` handleUpdate — UPDATE, 404 if rowsAffected==0 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:167` handleDelete — DELETE, 204/404 |
| R7 | SQLite / embedded DB | ✓ implemented | `main.go:30` sql.Open("sqlite3", "books.db"); mattn/go-sqlite3 |
| R8 | JSON responses + status codes | ✓ implemented | success paths encode JSON with 201/200/204/404; **caveat:** error bodies are plain text (low finding) |
| R9 | Validation: title+author required | ✓ implemented | `main.go:76`,`147` reject empty title/author with 400 |
| R10 | GET /health | ✓ implemented | `main.go:184` handleHealth returns {"status":"ok"}; tested `book_test.go:163` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, endpoints, tests sections |
| R12 | ≥3 tests | ✓ implemented | 4 tests in `book_test.go` (create/get, list/filter, update/delete, health) |

## Build & Test

Build/test were not re-run — stored scores are authoritative (per skill Step 2).

```text
scores.json
test_coverage = 0.596   # >0 ⇒ build + all tests executed and passed
defect_rate   = 1.0     # build+test succeeded
code_quality  = 0.9556
maintainability = 0.9667
idiomatic     = 0.52
```

Test functions (`grep -cE "^func Test" book_test.go` = 4), 0 skips
(`grep t.Skip` = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 367 (main.go 187, book_test.go 180) |
| Files | 8 |
| Dependencies | gorilla/mux, mattn/go-sqlite3 (go.sum 4 lines) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Statement coverage | 59.6% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R8 — error responses are plain text (`http.Error`), not JSON; success paths are JSON
2. [info] Statement coverage 59.6% despite all tests passing — main()/initDB/DB-error branches unexercised

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=go_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep2
cat scores.json                       # stored build/test/lint scores
grep -cE "^func Test" book_test.go    # test count = 4
grep -rE "t\.Skip\(" . --include="*.go" | wc -l  # skips = 0
# (build/test not re-run — scores.json is authoritative)
```
