# Evaluation: rest-api-crud · agent=codex effort=low language=clojure model=gpt-6.2-sol prompt=neutral · rep 1

## Summary

- **Factors:** language=clojure, model=gpt-6.2-sol, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 5 deftest / all passed / 0 skipped (5 effective) — from `test_coverage=1.0`
- **Build:** pass — from stored scores (not re-run)
- **Lint:** pass — `code_quality=0.95` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Scores read from `scores.json` (inline gate output), not re-run:
`test_coverage=1.0`, `code_quality=0.95`, `defect_rate=0.828`, `maintainability=0.932`,
`idiomatic=0.30`, `token_efficiency=0.0243`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `core.clj:50-54` collection-route :post → `db.clj:45-48` create! |
| R2 | GET /books lists all | ✓ implemented | `core.clj:46-49` → `db.clj:50-53` list-books |
| R3 | GET /books ?author= filter | ✓ implemented | `core.clj:46` reads author param → `db.clj:51-52` WHERE author=? |
| R4 | GET /books/{id} single book | ✓ implemented | `core.clj:59-61` → `db.clj:55-56` get-book; 404 when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `core.clj:62-66` → `db.clj:58-61` update! (full replace) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `core.clj:67-69` → `db.clj:63-66` delete! (204/404) |
| R7 | Data stored in SQLite | ✓ implemented | `db.clj:34-43` CREATE TABLE via JDBC; `project.clj` sqlite-jdbc dep |
| R8 | JSON responses + status codes | ✓ implemented | `core.clj:10-13` response; 201/200/404/400/405/204/500 present |
| R9 | title & author required | ✓ implemented | `core.clj:22-30` validation-error; test `validates-create-and-update:64` |
| R10 | GET /health endpoint | ✓ implemented | `core.clj:77-79` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, API table, test/build |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test/book_api/core_test.clj` 5 deftest; `test_coverage=1.0` |

## Build & Test

Not re-run — scores read from `scores.json` (per the evaluate-run skill; the toolchain
already ran during scoring).

```text
test_coverage = 1.0   ⇒ lein build + all tests passed
code_quality  = 0.95  ⇒ clean lint
```

`.lein-failures` is `{}` (no test failures). The agent additionally attempted a packaged
uberjar smoke test, but the harness **rejected** that shell command (`rm -f` style command
blocked — see `_agent_stderr.log`); this is a sandbox restriction on the agent's own
verification step, not a defect in the generated code, which the Ring-level integration
tests exercise directly.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: core + db) | ~163 |
| Lines of code (incl. test + project.clj) | 260 |
| Files (source) | 5 |
| Dependencies | 4 (clojure, ring-jetty, cheshire, sqlite-jdbc) |
| Tests total | 5 deftest |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=1.0) |

## Findings

No critical/high/medium findings. Top items (full list in `findings.jsonl`):

1. [low] N1 — A fresh JDBC connection is opened per request with no pooling (`db.clj:25-32`)
2. [info] E1 — Validation and error handling exceed the spec (`core.clj:22-30,35-38,88-91`)
3. [info] E2 — Parameterized SQL + `RETURNING *` avoid read-after-write (`db.clj:4-16,46-48`)

## Reproduce

```bash
cd experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=clojure_model=gpt-6.2-sol_prompt=neutral/rep1
cat scores.json                      # stored mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json        # pinned 12-requirement checklist
# lein test                          # would re-run; test_coverage=1.0 already recorded
```
