# Evaluation: language=go_model=sonnet-5_prompt=bdd · rep 1

## Summary

- **Factors:** language=go, model=sonnet-5, prompt=bdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (+ 4/4 BDD prompt instructions followed)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass — from `defect_rate=1.0` in scores.json (not re-run)
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Coverage:** 68% — `test_coverage=0.68` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 3 low, 2 info)

## Requirements

Pinned checklist from `REQUIREMENTS.json` (constant denominator across all runs of this task).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `handlers.go:38 handleCreateBook` → `store.go:Create` INSERT |
| R2 | GET /books lists all | ✓ implemented | `handlers.go:59 handleListBooks` → `store.go:List` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:List` `WHERE author = ?`; handler reads `r.URL.Query().Get("author")` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `handlers.go:68 handleGetBook`; `ErrNotFound`→404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:86 handleUpdateBook` → `store.go:Update` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.go:114 handleDeleteBook` → `store.go:Delete`, 204 |
| R7 | Data stored in SQLite | ✓ implemented | `main.go` `modernc.org/sqlite`; `store.go:migrate` CREATE TABLE books |
| R8 | JSON responses + correct status codes | ✓ implemented | `writeJSON`/`writeError`; 201/200/404/400/204 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `models.go:Validate`; test `Test_given_missing_title.../..._author...` |
| R10 | GET /health | ✓ implemented | `handlers.go:35 handleHealth` returns `{"status":"ok"}` |
| R11 | README.md setup + run | ✓ implemented | `README.md` — Setup, Run, API, Testing sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 11 test funcs in `api_test.go`; `test_coverage=0.68` (>0) |

### Prompt instructions (bdd)

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | Given/When/Then sections | ✓ | `api_test.go` — every test has `// Given` / `// When` / `// Then` comments |
| P2 | Name tests after behaviours, not implementation | ✓ | e.g. `Test_given_existing_book_when_deleted_then_it_can_no_longer_be_fetched` |
| P3 | One assertion per scenario where practical | ✓ | Most tests assert a single observable outcome (status/value) |
| P4 | Descriptive `given_when_then` test names | ✓ | All 11 tests use the `Test_given_..._when_..._then_...` convention |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (populated by retort's scorers at run time):

```text
scores.json: {"code_quality": 1.0, "test_coverage": 0.68, "defect_rate": 1.0,
              "maintainability": 0.9062, "idiomatic": 0.7, "token_efficiency": 0.0092}
```

- `defect_rate=1.0` ⇒ build + tests succeeded.
- `test_coverage=0.68` ⇒ tests executed; 68% statement coverage (error/500 branches largely untested).
- `code_quality=1.0` ⇒ lint clean.
- 0 skipped tests (`grep t.Skip` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go, incl. tests) | 582 |
| Source LOC (excl. api_test.go) | 328 |
| Files (excl. .git) | 15 |
| Dependencies (go.sum lines) | 21 (all transitive of `modernc.org/sqlite`) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Coverage | 68% |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] Test coverage 68% — error/500/invalid-id branches unexercised (`handlers.go:64,90`)
2. [low] No request body size limit on POST/PUT (`handlers.go:40` unbounded `json.Decode`)
3. [low] go.mod Go version (1.26.4) disagrees with README (1.22+)
4. [info] List endpoint has no pagination (not spec-required)
5. [info] PUT requires full book; no partial (PATCH) update (not spec-required)

No critical or high findings. This is a complete, idiomatic, clean run: all 12 pinned
requirements implemented, all 4 BDD prompt instructions followed, build+lint clean, no skipped tests.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=go_model=sonnet-5_prompt=bdd/rep1
cat scores.json                       # mechanical scores (build/test/lint) — not re-run
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count = 0
grep -cE "^func Test" api_test.go      # 11 test functions
# to independently re-verify (optional): go test ./... -cover
```
