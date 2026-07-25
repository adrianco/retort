# Evaluation: go · hermes-local · Qwen3-Coder-Next-4bit (m80, neutral) · rep 3

## Summary

- **Factors:** language=go, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — defect_rate=1.0 from scores.json (build + tests succeeded)
- **Lint:** pass — code_quality=0.9556 from scores.json
- **Architecture:** single-file Go net/http service (`main.go`) with `APIHandler` over `database/sql` + go-sqlite3; run-summary skill unavailable in this session
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:189` createBook — decodes+validates+inserts, 201 |
| R2 | GET /books lists all | ✓ implemented | `main.go:116` getAllBooks (see low finding on empty→null) |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:144` getBooksByAuthor, parametrized `WHERE author = ?` |
| R4 | GET /books/{id} single, 404 | ✓ implemented | `main.go:172` getBook — `sql.ErrNoRows`→404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:220` updateBook — RowsAffected==0→404 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:254` deleteBook — 204, RowsAffected==0→404 |
| R7 | SQLite / embedded DB | ✓ implemented | `main.go:13,37` go-sqlite3, `sql.Open("sqlite3", ...)`, real table |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/204/400/404/500 set throughout; Content-Type json |
| R9 | Validation title+author required | ✓ implemented | `main.go:70` validateBook → 400; TestCreateBookValidation |
| R10 | GET /health | ✓ implemented | `main.go:276` healthHandler returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — prerequisites, install, run, endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | `main_test.go` — 12 tests, all endpoints + error cases |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
test_coverage=0.65   defect_rate=1.0   code_quality=0.9556
maintainability=0.9813   idiomatic=0.8   token_efficiency=0.0127
```

`defect_rate=1.0` ⇒ build + all tests passed. `test_coverage=0.65` is the Go
statement-coverage fraction (65%), not a pass-rate — all 12 tests execute and
pass (agent stdout: "12/12 tests passing"). No skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.go + main_test.go) | 307 + 477 = 784 |
| Files (excl .git) | 13 |
| Dependencies (go.sum lines) | 2 (go-sqlite3) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Coverage (Go stmt) | 65% |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] R2 — empty book list serializes as JSON `null` not `[]` (`main.go:125` nil slice)
2. [low] TestMain writes a stray `./books.db` into the workspace despite tests using `:memory:` (`main_test.go:465`)
3. [info] enhancement — 12 tests, far exceeding the 3-test minimum

No critical/high/medium findings. This is a clean, fully-conformant run.

## Reproduce

```bash
cd experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop/runs/agent=hermes-local_language=go_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep3
cat scores.json                                   # mechanical scores (not re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" main_test.go                # 13 (12 tests + TestMain)
# to actually run: go test ./...
```
