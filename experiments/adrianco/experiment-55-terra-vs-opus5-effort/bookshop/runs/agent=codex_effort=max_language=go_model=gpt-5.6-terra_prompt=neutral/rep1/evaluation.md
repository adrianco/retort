# Evaluation: agent=codex_effort=max_language=go_model=gpt-5.6-terra_prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=gpt-5.6-terra, agent=codex, effort=max, prompt=neutral, framework=stdlib (`net/http`)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective); coverage 0.607–0.66 from retort.db
- **Build:** pass — from `defect_rate=1.0` (retort.db); not re-run
- **Lint:** pass — `code_quality=1.0` (retort.db)
- **Architecture:** `run-summary` skill not available in this session; see inline module notes below
- **Findings:** 0 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `api.go:88 createBook` → `store.go:79 Create`; `api_test.go:51` |
| R2 | GET /books lists all books | ✓ implemented | `api.go:102 listBooks` → `store.go:100 List` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:103 WHERE author = ?`; `api_test.go:91 TestListBooksCanFilterByAuthor` |
| R4 | GET /books/{id} single book | ✓ implemented | `api.go:111 getBook`; 404 via `ErrNotFound`; `api_test.go:60,85` |
| R5 | PUT /books/{id} update | ✓ implemented | `api.go:124 updateBook` → `store.go:147 Update`; `api_test.go:68` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `api.go:142 deleteBook` → `store.go:168 Delete` (204); `api_test.go:77` |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:9 modernc.org/sqlite`, `store.go:39 sql.Open("sqlite", …)`, migrate at `store.go:57` |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON`/`writeError` `api.go:199-211`; 201/200/204/400/404/405 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `api.go:172` rejects blank title/author (400); `api_test.go:120 TestBookValidation…` |
| R10 | GET /health endpoint | ✓ implemented | `api.go:44 handleHealth` → `{"status":"ok"}`; `api_test.go:146 TestHealth` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run, config env vars, API table, curl examples, Test section |
| R12 | ≥3 unit/integration tests | ✓ implemented | 4 `Test*` funcs in `api_test.go`; `test_coverage > 0` |

Enhancements beyond spec (not deductions): request-body size cap (`MaxBytesReader`, `api.go:157`), `DisallowUnknownFields` + trailing-JSON rejection, `Allow` header on 405, graceful shutdown with signal handling (`main.go:44-52`), `ReadHeaderTimeout`, negative-year validation.

## Build & Test

Not re-run — scores read from `retort.db` / `scores.json` per skill policy.

```text
defect_rate = 1.0   → build + tests succeeded
code_quality = 1.0  → lint/quality clean (go vet / gofmt)
test_coverage = 0.607 (retort.db) / 0.66 (scores.json)
4 tests, 0 skips (grep t.Skip → none)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 458 (api 211, store 194, main 53) |
| Test LOC | 160 |
| Files (source) | 5 (.go) + go.mod/go.sum + README |
| Dependencies (go.sum lines) | 41 (single direct: modernc.org/sqlite) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Test coverage | 0.607 (retort.db) |
| Duration | 187.2s |
| Tokens | 265,791 |
| Cost | $0.25 |

## Findings

None. All 12 pinned requirements are implemented and exercised by tests; build/tests/lint all pass; no skipped or disabled tests. `findings.jsonl` is empty.

Note: `_agent_stderr.log` shows the agent's `rm -f` cleanup command was rejected by the codex sandbox (a stray `bookcollection` binary could not be removed). This did not affect the deliverables and is a harness-sandbox artifact, not a code defect.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=max_language=go_model=gpt-5.6-terra_prompt=neutral/rep1"
go test ./...          # build + run tests (already scored: defect_rate=1.0)
grep -rEc "t\.Skip\(|t\.Skipf\(" . --include="*.go"   # → 0 skips
```
