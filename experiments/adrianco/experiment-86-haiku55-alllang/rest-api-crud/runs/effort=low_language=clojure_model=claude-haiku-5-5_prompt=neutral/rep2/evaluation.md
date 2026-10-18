# Evaluation: effort=low language=clojure model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=clojure, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — from `test_coverage=1.0` in scores.json (build+tests ran and passed)
- **Lint:** pass — `code_quality=0.967` in scores.json, 0 warnings observed
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `handler.clj:handle-create` → `db.clj:create-book!` (INSERT ... RETURNING *), 201 |
| R2 | GET /books lists all books | ✓ implemented | `handler.clj:handle-list` → `db.clj:list-books` |
| R3 | GET /books ?author= filter | ✓ implemented | `handler.clj:48` reads `query-params "author"`; `db.clj:list-books` filters `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `handler.clj:handle-get` → `db.clj:find-book`, 404 branch |
| R5 | PUT /books/{id} updates | ✓ implemented | `handler.clj:handle-update` → `db.clj:update-book!` (UPDATE ... RETURNING *) |
| R6 | DELETE /books/{id} | ✓ implemented | `handler.clj:handle-delete` → `db.clj:delete-book!`, 204 |
| R7 | Data in SQLite / embedded DB | ✓ implemented | `db.clj` uses sqlite-jdbc + next.jdbc; file-backed datasource |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `json-response` sets Content-Type + Cheshire body; 201/200/204/400/404/405/422/500 |
| R9 | Validation: title & author required | ✓ implemented | `validation.clj:validate-book` rejects blank title/author; tested at `handler_test.clj:validation-rejects-missing-title-and-author` (see low finding re: 422 vs 400) |
| R10 | GET /health | ✓ implemented | `handler.clj:handle-health` returns 200 `{"status":"ok"}` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — Requirements, Run, Test, Endpoints, status codes, examples, layout |
| R12 | ≥3 unit/integration tests | ✓ implemented | 13 deftests across `handler_test.clj` (9) + `validation_test.clj` (4); `test_coverage=1.0` |

No prompt-factor requirements: `prompt=neutral` is the baseline instruction, no `prompts/` additions.

## Build & Test

Not re-run — stored mechanical scores from `scores.json` are authoritative:

```text
test_coverage   = 1.0     → build + all tests executed and passed
code_quality    = 0.9667
defect_rate     = 0.9340  → build+test succeeded
maintainability = 0.9327
idiomatic       = 0.82
```

Test runner: `clojure -M:test` (`test/book_api/runner.clj` runs both namespaces, non-zero exit on failure). Integration tests drive the Ring handler against a real temp SQLite file; validation tested as units. No skipped/disabled tests (`grep` for `comment`/`#_`/skip markers = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests, .clj) | 353 |
| Files (excl. .git, agent logs) | 16 |
| Dependencies (deps.edn mvn) | 6 |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores from archive) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R9 validation returns 422, not the 400 the spec's how-to-verify note cites — defensible choice; validation itself is correct and tested.
2. [info] Enhancement — robust routing/error handling beyond spec (405, malformed-body 400, 404 for bad routes/ids, 500 catch-all).

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=clojure_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                 # stored mechanical scores (build/test/lint)
cat ../../REQUIREMENTS.json      # pinned 12-item checklist
grep -rnE "\(comment|#_\(deftest|:skip" src test   # skip detection (0)
grep -rcE "\(deftest" test       # test counts
find src test -name '*.clj' -exec wc -l {} +        # LOC
# Optional full re-run (slow): clojure -M:test
```
