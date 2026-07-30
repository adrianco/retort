# Evaluation: agent=codex effort=medium language=go model=gpt-5.6-terra prompt=neutral · rep 2

## Summary

- **Factors:** language=go, agent=codex, model=gpt-5.6-terra, effort=medium, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.956 from scores.json
- **Architecture:** single-file `net/http` handler over `modernc.org/sqlite` (see notes below; run-summary skill unavailable)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Using the pinned checklist in `bookshop/REQUIREMENTS.json` (12 fixed requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:77-89` INSERT of all four fields, 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `main.go:90-117` SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:91-96` adds `WHERE author = ?`; test `main_test.go:60` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.go:125-135` + `find`; `sql.ErrNoRows`→404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:136-152` UPDATE, 404 when RowsAffected==0 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:153-164` DELETE, 204/404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `main.go:15` `modernc.org/sqlite`; table created `main.go:33-39` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `writeJSON`/`writeError` `main.go:197-208`; 201/200/204/400/404/405/500 used |
| R9 | Input validation: title & author required | ✓ implemented | `main.go:189-193` trims and rejects empty with 400; test `main_test.go:76` |
| R10 | GET /health endpoint | ✓ implemented | `main.go:46-53` returns `{"status":"ok"}`; test `main_test.go:86` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` run/test/endpoint docs |
| R12 | At least 3 unit/integration tests | ✓ implemented | 3 `func Test*` in `main_test.go`; test_coverage=0.614 (>0) |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
defect_rate      = 1.0    → build + tests succeeded
test_coverage    = 0.614  → tests executed and passed; 61.4% coverage
code_quality     = 0.956
maintainability  = 0.891
idiomatic        = 0.77
token_efficiency = 0.035
```

Skipped tests: `grep t.Skip` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 320 (main.go 231, main_test.go 89) |
| Files (excl. .gocache/.git) | 13 |
| Dependencies (go.sum lines) | 41 |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Coverage | 61.4% |

## Findings

No requirement, build, or test defects. Two info-level enhancement notes (full list in `findings.jsonl`):

1. [info] PUT is a full replace with no id-vs-body reconciliation — acceptable for spec.
2. [info] GET /books has no pagination — not required by TASK.md.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=medium_language=go_model=gpt-5.6-terra_prompt=neutral/rep2"
cat scores.json
grep -cE "^func Test" main_test.go
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
# build/test already scored: defect_rate=1.0, test_coverage=0.614 — do not re-run per skill
```
