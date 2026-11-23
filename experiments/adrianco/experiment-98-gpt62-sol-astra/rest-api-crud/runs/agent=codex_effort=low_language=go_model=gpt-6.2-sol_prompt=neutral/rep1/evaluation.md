# Evaluation: agent=codex effort=low language=go model=gpt-6.2-sol prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=gpt-6.2-sol, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass (from `scores.json`: defect_rate=1.0, test_coverage=0.767)
- **Lint:** pass — code_quality=0.9556, idiomatic=0.87, maintainability=1.0 (from `scores.json`)
- **Architecture:** single-file Go `net/http` service (`main.go`) over `modernc.org/sqlite`; `run-summary` not invoked (trivial one-file codebase — see Build & Test).
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

The prompt factor is `neutral`, whose text (`prompts/neutral.md`) prescribes no methodology beyond "include tests"; it adds no checkable `P*` requirements. The pinned `REQUIREMENTS.json` (12 entries) is used verbatim as the checklist.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:83,161` `create` INSERT … RETURNING id |
| R2 | GET /books lists all books | ✓ implemented | `main.go:84,178` `list` returns JSON array |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:181-184` adds `WHERE author = ?`; `TestListAndAuthorFilter` main_test.go:88 |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.go:85,207` `get`; 404 via `checkBookResult` main.go:249-251 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:86,221` `update` UPDATE … RETURNING id |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:87,238` `delete` DELETE … RETURNING id, 204 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `main.go:15,34-52` `modernc.org/sqlite`, `CREATE TABLE books` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `writeJSON` main.go:104; 201/200/204/400/404/405/503 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `main.go:128-130` rejects blank title/author → 400; `TestValidation` main_test.go:94 |
| R10 | GET /health health check | ✓ implemented | `main.go:82,153` `health` pings DB, 200/503 |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` setup/run/API/tests sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 4 tests in main_test.go; test_coverage=0.767 (>0) |

## Build & Test

Build/test not re-run — stored scores read from `scores.json` (inline gate output):

```text
scores.json: {"code_quality": 0.9556, "token_efficiency": 0.0319,
              "test_coverage": 0.767, "defect_rate": 1.0,
              "maintainability": 1.0, "idiomatic": 0.87}
```

- `test_coverage=0.767` ⇒ build succeeded and tests executed (76.7% coverage).
- `defect_rate=1.0` ⇒ build + tests passed.

```text
go test ./...   (4 tests, from main_test.go)
TestBookLifecycle           full CRUD round-trip + 404s on deleted id
TestListAndAuthorFilter     empty array, two inserts, ?author= filter
TestValidation              400 on blank/garbage/trailing-JSON bodies, 405, 404, 400 bad id
TestPersistenceAndHealth    on-disk SQLite persistence + /health 200/503
```

Skip scan (`t.Skip`/`t.Skipf`): 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 389 (main.go 256, main_test.go 133) |
| Files | 12 (incl. go.mod/go.sum/logs) |
| Dependencies (go.sum lines) | 43 |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| test_coverage | 0.767 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Robustness beyond spec: 405 Allow header, 1 MiB body cap, trailing-JSON rejection — `main.go:88-90,121,125-133`

No requirement, build, test, or skip findings. Run is clean.

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=go_model=gpt-6.2-sol_prompt=neutral/rep1"
cat scores.json                                    # stored mechanical scores
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
grep -rE "^func Test" main_test.go
go test ./...                                      # fallback only; scores already stored
```
