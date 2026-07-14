# Evaluation: agent=hermes-local language=go prompt=neutral · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local (model Qwen3.6-35B-A3B), framework=none (stdlib `net/http`), prompt=neutral
- **Status:** ok (all requirements met; one persistence/concurrency defect on R7)
- **Requirements:** 11/12 implemented, 1 partial (R7), 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (11 test funcs, 3 sub-cases; 13 effective)
- **Build:** pass — `defect_rate=1.0` from scores.json (build + tests succeeded)
- **Lint:** pass — `code_quality=1.0` from scores.json (1 low dead-code note)
- **Coverage:** 50.3% (`test_coverage=0.503`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 1 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create | ✓ implemented | `handlers.go:94 createBook`, `database.go:52 CreateBook`; TestCreateBook |
| R2 | GET /books list | ✓ implemented | `handlers.go:76 listBooks`, `database.go:76 GetAllBooks`; TestListBooks |
| R3 | ?author= filter | ✓ implemented | `database.go:80-84` author WHERE clause; TestListBooks filter case |
| R4 | GET /books/{id} + 404 | ✓ implemented | `handlers.go:126 getBook`, `database.go:108`; TestGetBook / TestGetBookNotFound |
| R5 | PUT /books/{id} update | ✓ implemented | `handlers.go:142 updateBook`, `database.go:123 UpdateBook`; TestUpdateBook |
| R6 | DELETE /books/{id} | ✓ implemented | `handlers.go:178 deleteBook`, `database.go:151`; TestDeleteBook / TestDeleteBookNotFound |
| R7 | SQLite/embedded persistence | ~ partial | Uses `mattn/go-sqlite3` (`database.go:20`) but DSN is `:memory:` (`main.go:15`) over a pooled sql.DB — non-persistent + unsafe under concurrency (see Findings) |
| R8 | JSON + correct status codes | ✓ implemented | `models.go:42 writeJSON`; 201/200/204/400/404/500 across handlers.go |
| R9 | title & author required | ✓ implemented | `handlers.go:102-113` (create) & `:150-161` (update); TestCreateBookValidation / TestUpdateBookValidation |
| R10 | GET /health | ✓ implemented | `handlers.go:23 Health` → `{"status":"ok"}`; TestHealth |
| R11 | README with setup/run | ✓ implemented | `README.md` — prerequisites, build/run, test, curl examples |
| R12 | ≥3 tests, run | ✓ implemented | 11 test funcs (`main_test.go`), test_coverage=0.503 > 0 |

Prompt factor `neutral` prescribes no methodology and asks for tests that demonstrate the requirements — satisfied by the 11-function suite.

## Build & Test

Build/test not re-run — stored mechanical scores are authoritative (skill step 2):

```text
scores.json: {"code_quality": 1.0, "test_coverage": 0.503, "defect_rate": 1.0,
              "maintainability": 0.867, "idiomatic": 0.78, "token_efficiency": 0.0107}
defect_rate=1.0  -> go build + go test succeeded
test_coverage=0.503 -> tests executed; 50.3% statement coverage
```

Agent's own run log (`_agent_stdout.log`) reports 11/11 tests PASS; grep confirms 0 `t.Skip` calls.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go, non-test) | 472 |
| Lines of code (tests) | 418 |
| Source files (go + mod/sum + README) | 8 |
| Dependencies (direct) | 1 (`github.com/mattn/go-sqlite3`) |
| Tests total | 13 (11 funcs + 3 sub-cases, 1 shared) |
| Tests effective | 13 (0 skipped) |
| Skip ratio | 0% |
| Coverage | 50.3% |

## Findings

Full list in `findings.jsonl`:

1. **[high]** R7 — SQLite store is `:memory:` over a pooled sql.DB: non-persistent across restarts, and each pooled connection is a separate in-memory DB → `no such table` / lost writes under concurrent requests. Tests pass only because they run sequentially. Fix: file-backed DSN or `SetMaxOpenConns(1)` + shared cache.
2. **[low]** Dead code — `HandleBooks` / `HandleBookByID` (handlers.go:34,46) are unused; main.go wires routes via inline closures.
3. **[info]** Coverage 50.3% — `main()` mux wiring, path parsing, and method-not-allowed dispatch are untested (handlers tested directly, bypassing the mux).

## Reproduce

```bash
cd experiment-18-hermes-35b-lcm/bookshop/runs/agent=hermes-local_language=go_prompt=neutral/rep1
cat scores.json                          # stored build/test/lint scores (authoritative)
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
wc -l main.go handlers.go database.go models.go               # 472 non-test LoC
# Optional live re-run (not required by skill):
go build -o book-api && go test -cover ./...
```
