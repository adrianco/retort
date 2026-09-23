# Evaluation: agent=codex effort=default language=go model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.9556 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

Scores read from `scores.json` (inline gate; not re-run): test_coverage=0.615,
defect_rate=1.0, code_quality=0.9556, maintainability=0.9846, idiomatic=0.78,
token_efficiency=0.0136. `defect_rate=1.0` ⇒ build + tests passed; `test_coverage=0.615`
is the coverage fraction, not a pass/fail gate.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:177 createBook` → `INSERT`; tested `main_test.go:41` |
| R2 | GET /books lists all | ✓ implemented | `main.go:147 listBooks` → `SELECT ... ORDER BY id` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:150-153`; tested `main_test.go:74` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.go:105-114` sql.ErrNoRows→404; tested `main_test.go:54,109` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:115-131` UPDATE, 404 on 0 rows; tested `main_test.go:101` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:132-143` DELETE→204, 404 on 0 rows; tested `main_test.go:105` |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:14,22` go-sqlite3 `sql.Open("sqlite3")`, `initDB` schema |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON`/`writeError`; 201/200/204/400/404/405/500/503 used |
| R9 | title+author required (400) | ✓ implemented | `main.go:207-212 decodeBook`; tested `main_test.go:60` |
| R10 | GET /health | ✓ implemented | `main.go:68-74` pings DB; tested `main_test.go:115` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Requirements/Run/API/Tests sections |
| R12 | ≥3 tests | ✓ implemented | 5 test funcs in `main_test.go`; test_coverage=0.615 > 0 |

Enhancements beyond spec (not deductions): strict body decoding
(`DisallowUnknownFields`, `MaxBytesReader` 1 MiB, single-object enforcement),
per-request `context` propagation, `/health` verifies DB connectivity, `405` with
`Allow` header on wrong methods, `PORT`/`BOOKS_DB_PATH` env configuration.

## Build & Test

Build/test not re-run — stored scores used per skill (defect_rate=1.0 ⇒ green).

```text
go test ./...   (per README; result reflected in scores.json)
defect_rate=1.0  → build compiled, all tests passed
test_coverage=0.615 → statement coverage fraction
5 test functions, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 232 (main.go) + 120 (main_test.go) = 352 |
| Files (excl. agent logs) | 8 |
| Dependencies | 1 direct (`github.com/mattn/go-sqlite3`) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All 12 pinned requirements implemented, tests pass, no skipped/disabled tests,
no build or lint failures. `findings.jsonl` is empty.

## Reproduce

```bash
cd experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=go_model=gpt-6-luna_prompt=neutral/rep1
cat scores.json                    # stored mechanical scores (build/test/lint)
grep -rEc "t\.Skip\(|t\.Skipf\(" . --include="*.go"   # skip detection → 0
grep -hE "^func Test" *.go | wc -l # test count → 5
# build/test intentionally NOT re-run (defect_rate=1.0 already recorded)
```
