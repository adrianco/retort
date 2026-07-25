# Evaluation: go · hermes-local · gpt-oss-20b · rep 3 (SECOND OPINION)

## Summary

- **Factors:** language=go, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok
- **Requirements:** 10/12 implemented, 1 partial (R12), 1 missing (R11)
- **Tests:** build+tests pass (defect_rate=1.0), test_coverage=0.669; 2 test functions, 0 skipped (2 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 1 high, 1 medium)

## Second-opinion re-check of prior claim

The first evaluation scored requirement_coverage=0.8333 and flagged **R11 (README.md)** as
missing. **I re-checked this claim and CONFIRM it — the first evaluator was correct.**

Evidence I gathered before accepting "missing":
- `find . -iname "*readme*"` returns nothing — no README file exists on disk.
- The generated workspace contains only `go.mod`, `go.sum`, `main.go`, `db.go`,
  `router.go`, `router_test.go` — no docs.
- `_hermes_session.jsonl` contains exactly **5 `write_file` tool calls**, targeting
  `go.mod`, `main.go`, `db.go`, `router.go`, `router_test.go`. **There is no `write_file`
  call for README.md.** The string `README.md` appears only in the model's *reasoning*
  ("Also create README", "Also need to create README.md") — it planned the file but never
  emitted a write for it.
- Note: unlike the first evaluator's phrasing, `_agent_stdout.log` does **not** claim a
  README was created — its file list omits README entirely, consistent with the disk state.

R11 is therefore genuinely absent. Verdict unchanged.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `router.go:42` createBookHandler, INSERT at :53, 201 at :61 |
| R2 | GET /books lists books | ✓ implemented | `router.go:65` listBooksHandler |
| R3 | GET /books ?author= filter | ✓ implemented | `router.go:66,70-71` filters WHERE author=? |
| R4 | GET /books/{id} single book | ✓ implemented | `router.go:92` getBookHandler, 404 at :103 |
| R5 | PUT /books/{id} updates | ✓ implemented | `router.go:110` updateBookHandler, UPDATE at :127, 404 at :133 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `router.go:141` deleteBookHandler, 204 at :158 |
| R7 | SQLite / embedded DB | ✓ implemented | `db.go:7,22` go-sqlite3, CREATE TABLE :27-34 |
| R8 | JSON + proper status codes | ✓ implemented | 201/200/404/400/204 across router.go; Content-Type application/json |
| R9 | Validation: title+author required | ✓ implemented | `router.go:48` (create) & `:122` (update) → 400 |
| R10 | GET /health | ✓ implemented | `router.go:25,37` healthHandler → {"status":"ok"} |
| R11 | README.md with setup/run | ✗ missing | No README on disk; no write_file call in session (see re-check above) |
| R12 | At least 3 tests | ~ partial | `router_test.go` has only 2 test funcs (TestHealth :20, TestCRUD :38); tests run (test_coverage=0.669) |

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
code_quality=1.0  defect_rate=1.0  test_coverage=0.669  maintainability=0.786  idiomatic=0.58
```

`defect_rate=1.0` ⇒ build + tests succeeded. `go test ./...` per agent stdout → `ok`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 307 (.go) + 8 (go.mod) |
| Files | 11 |
| Dependencies (go.sum lines) | 4 |
| Tests total (funcs) | 2 |
| Tests effective | 2 |
| Skip ratio | 0% |
| Build | pass |

## Findings

1. [high] R11 — README.md missing despite being a required deliverable
2. [medium] R12 — only 2 test functions; deliverable asks for at least 3

## Reproduce

```bash
cd runs/agent=hermes-local_language=go_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep3
find . -iname "*readme*"                        # empty → no README
grep -oE '"name": "write_file"' _hermes_session.jsonl | wc -l   # 5 writes, none README
grep -cE '^func Test' router_test.go            # 2
cat scores.json                                 # defect_rate=1.0, test_coverage=0.669
```
