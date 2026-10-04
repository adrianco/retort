# Evaluation: agent=codex effort=low language=go model=gpt-6-astra prompt=neutral · rep 2

## Summary

- **Factors:** language=go, agent=codex, model=gpt-6-astra, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 5 test functions + subtests, all passing / 0 failed / 0 skipped (coverage 73.7%)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.9556 from scores.json
- **Architecture:** single-package `net/http` service, 2 source files; see Metrics
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

Denominator fixed by `rest-api-crud-72/REQUIREMENTS.json` (12 requirements, verbatim).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:207-219` INSERT, 201 + Location; `main_test.go:38` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:132-159` list(); `main_test.go:67` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:135-138` WHERE author=?; `main_test.go:78` |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:161-173` get(), 404 on ErrNoRows; `main_test.go:50` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:220-235` UPDATE, 404 if absent; `main_test.go:54` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:239-255` DELETE, 204/404; `main_test.go:60` |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:17,37-56` modernc.org/sqlite + CREATE TABLE; `main_test.go:123` persistence across reopen |
| R8 | JSON responses + status codes | ✓ implemented | `main.go:60-66` respond() sets Content-Type/WriteHeader; 201/200/204/400/404/405/413/503 used |
| R9 | Validation: title & author required | ✓ implemented | `main.go:200-203` trims + rejects blank (400); `main_test.go:94` |
| R10 | GET /health endpoint | ✓ implemented | `main.go:76-89` pings DB, 200/503; `main_test.go:107` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run, API table, build & test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 5 `func Test*` in `main_test.go`; test_coverage=0.737 (>0) |

No requirement is missing or partial. Enhancements beyond spec (1 MiB body cap, unknown-field
rejection, SQL-injection test, 405+Allow, DB-liveness health check) are logged as info findings.

## Build & Test

Not re-run — stored mechanical scores read from `scores.json` (skill step 2):

```text
scores.json: {"code_quality": 0.9556, "token_efficiency": 0.0547, "test_coverage": 0.737,
              "defect_rate": 1.0, "maintainability": 0.9728, "idiomatic": 0.76}
```

- `defect_rate=1.0` ⇒ `go build` + `go test` succeeded.
- `test_coverage=0.737` ⇒ tests executed and passed, 73.7% statement coverage.
- `code_quality=0.9556` ⇒ lint/quality clean.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 423 (main.go 279, main_test.go 144) |
| Files (excl. .git) | 8 tracked (main.go, main_test.go, go.mod, go.sum, README.md, .gitignore, TASK.md, stack.json) |
| Dependencies | 1 direct (modernc.org/sqlite), 12 indirect; 41 go.sum lines |
| Tests total | 5 top-level + parameterized subtests |
| Tests effective | 5+ (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores from cache) |

## Findings

All 4 findings are info-level (no defects). Full list in `findings.jsonl`:

1. [info] Hardened input handling beyond spec (1 MiB cap, DisallowUnknownFields, single-object) — `main.go:176-199`
2. [info] SQL-injection + 405/Allow coverage in tests — `main_test.go:78,116`
3. [info] Health endpoint reports DB liveness (503), tested across reopen — `main.go:81-88`
4. [info] `year` accepts any integer incl. negatives (spec requires no year validation) — `main.go:200-203`

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-72/runs/agent=codex_effort=low_language=go_model=gpt-6-astra_prompt=neutral/rep2"
cat scores.json                 # stored mechanical scores (build/test/lint), not re-run
cat ../../../REQUIREMENTS.json   # pinned 12-requirement checklist
grep -cE "^func Test" main_test.go
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
# Optional re-verify: go build ./... && go test -cover ./...
```
