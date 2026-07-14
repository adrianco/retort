# Evaluation: agent=hermes-local · language=go · prompt=none · stack=s6 · rep 2

## Summary

- **Factors:** language=go, agent=hermes-local, prompt=none, stack=s6, framework=unknown
- **Status:** failed (non-delivery — only `models.go` was written; package does not build and has no tests)
- **Requirements:** 0/12 implemented, 0 partial, 12 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective) — `go test ./...` reports "no test files"
- **Build:** fail — `go build ./...` → `function main is undeclared in the main package`
- **Lint:** n/a — code_quality=0.9556 from scores.json applies only to the single scaffolding file
- **Architecture:** see `summary/index.md` (verdict: scaffolding only, effectively a non-delivery)
- **Findings:** 13 items in `findings.jsonl` (1 critical, 10 high, 1 medium, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create | ✗ missing | no handler/route; only `CreateBookRequest` DTO (`models.go:22`) |
| R2 | GET /books list | ✗ missing | no router/handler exists |
| R3 | GET /books ?author= filter | ✗ missing | no list handler exists |
| R4 | GET /books/{id} | ✗ missing | no route/handler |
| R5 | PUT /books/{id} update | ✗ missing | only `UpdateBookRequest` DTO (`models.go:30`) |
| R6 | DELETE /books/{id} | ✗ missing | no route/handler |
| R7 | SQLite/embedded persistence | ✗ missing | no `database.go`; `go.mod` has zero deps, no `go.sum` |
| R8 | JSON responses + status codes | ✗ missing | response DTOs declared but never serialized/returned |
| R9 | Validation (title/author required) | ✗ missing | no handler code to validate |
| R10 | GET /health | ✗ missing | `HealthResponse` type (`models.go:39`) but no `/health` route |
| R11 | README.md | ✗ missing | no `README.md` in run_dir |
| R12 | ≥3 unit/integration tests | ✗ missing | no `*_test.go`; `go test` → "no test files" |

All 12 pinned requirements (`../../REQUIREMENTS.json`) are unmet. The run wrote a single 40-line `models.go` containing only struct declarations (`Book`, `CreateBookRequest`, `UpdateBookRequest`, `ErrorResponse`, `HealthResponse`) and stopped. Per `_agent_stdout.log`, the agent hit a `write_file` guard against the temp path, planned a `cat` heredoc fallback for the remaining files (`database.go`, `handlers.go`, `main.go`, `books_test.go`, `README.md`), and never landed them.

## Build & Test

```text
go build ./...
# bookapi
runtime.main_main·f: function main is undeclared in the main package
```

```text
go test ./...
?   bookapi   [no test files]
```

> Note: `scores.json` reports `test_coverage=0.405` and `defect_rate=1.0`, which are **not credible** for a workspace that has zero test files and does not build. Ground truth was taken from a read-only build/test in a temp copy (workspace unmodified). Flagged as `score-anomaly` (info) in findings.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 40 (`models.go`) |
| Files (excl. summary/.git) | 10 (1 `.go` source) |
| Dependencies | 0 (no `go.sum`) |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | n/a (0 tests) |
| Build duration | fails immediately |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Package does not build — `main` package has no `func main`
2. [high] POST /books create endpoint missing (R1)
3. [high] GET /books list endpoint missing (R2)
4. [high] SQLite/embedded persistence layer missing (R7)
5. [high] No tests delivered; test gate fails (R12)

## Reproduce

```bash
cd "experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s6/rep2"
cat stack.json scores.json _agent_stdout.log
find . -name '*_test.go'          # empty
# read-only build/test in a temp copy (do not mutate run_dir):
tmp=$(mktemp -d); cp models.go go.mod "$tmp"/; cd "$tmp"
go build ./...                    # fails: function main is undeclared
go test ./...                     # no test files
```
