# Evaluation: agent=codex effort=low language=go model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `REQUIREMENTS.json`)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `scores.json` defect_rate=1.0 (build + tests succeeded; not re-run)
- **Lint:** pass — code_quality=0.9556 from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Checklist pinned by `rest-api-crud/REQUIREMENTS.json` (12 fixed requirements, used verbatim). The prompt factor `neutral.md` prescribes no methodology and adds no checkable requirements (P-list empty).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:80 createBook`, INSERT at `main.go:90`, 201 at `:100` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:103 listBooks`, SELECT at `:110` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:106-108` WHERE author=?; test `main_test.go:59` |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:144-154 getBook`, 404 at `:147` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:155-176` UPDATE, 404 on 0 rows at `:172` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:177-188` DELETE, 204 at `:188`, 404 at `:185` |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:34 sql.Open("sqlite",...)`, `modernc.org/sqlite`, schema `:39-45` |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON` `:224`; 201/200/204/400/404/405 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `main.go:214 validateBook`; test `main_test.go:67` |
| R10 | GET /health | ✓ implemented | `main.go:54-60` returns `{status:ok}`; test `main_test.go:91` |
| R11 | README with setup/run | ✓ implemented | `README.md` Run/Test/API sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 3 `func Test*` in `main_test.go`; test_coverage=0.599 (>0) |

## Build & Test

Not re-run — stored scores used per the evaluate-run skill (defect_rate=1.0 ⇒ build + all tests passed).

```text
# from scores.json
test_coverage   = 0.599   (line coverage; >0 ⇒ tests executed and passed)
defect_rate     = 1.0     (build + test succeeded)
code_quality    = 0.9556
maintainability = 0.8912
idiomatic       = 0.82
token_efficiency= 0.0419
```

3 tests, 0 skips (`grep t.Skip` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 252 (main.go) + 95 (main_test.go) = 347 |
| Files | 7 (main.go, main_test.go, go.mod, go.sum, README.md, TASK.md, stack.json) |
| Dependencies | 50 lines in go.sum (direct: `modernc.org/sqlite`) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Line coverage ~60% (test_coverage=0.599) — error-code branches (405/404/invalid-id, DB errors) untested
2. [info] Strict JSON decoding beyond spec (DisallowUnknownFields + trailing-object rejection)
3. [info] PUT is a full replace requiring title+author (consistent with spec)

No critical/high/medium findings. This run fully implements the spec and passes build + tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=go_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json                         # stored mechanical scores (build/test/lint)
grep -cE "^func Test" main_test.go       # test count = 3
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skips = 0
# full build+test (optional; already captured by defect_rate=1.0):
# go test ./...
```
