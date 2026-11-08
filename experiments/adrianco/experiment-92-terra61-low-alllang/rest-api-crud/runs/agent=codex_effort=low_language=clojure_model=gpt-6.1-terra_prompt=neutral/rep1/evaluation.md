# Evaluation: agent=codex effort=low language=clojure model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=clojure, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `test_coverage=1.0` in `scores.json`/`retort.db`
- **Lint:** pass — `code_quality=0.95` in `scores.json`
- **Architecture:** single-namespace Ring service (`src/books/core.clj`); `run-summary` skill unavailable, so no `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

## Requirements

Denominator fixed by the pinned `REQUIREMENTS.json` (12 entries).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/books/core.clj:78-86` — INSERT + 201 + Location header |
| R2 | GET /books lists all | ✓ implemented | `src/books/core.clj:72-76` — `SELECT * ... ORDER BY id` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/books/core.clj:74-75` — filters on `params "author"` |
| R4 | GET /books/{id} single book | ✓ implemented | `src/books/core.clj:88-90` — 200 / 404; `find-book` :54 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/books/core.clj:92-99` — UPDATE, 404 if no row |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/books/core.clj:101-105` — DELETE, 404 if no row |
| R7 | Data stored in SQLite | ✓ implemented | `deps.edn` sqlite-jdbc; `connect` `jdbc:sqlite:` :8-14 |
| R8 | JSON responses + status codes | ✓ implemented | `response`/`error` :36-40; 201/200/400/404 throughout |
| R9 | Validation: title & author required | ✓ implemented | `valid-book?` :42-46 — non-blank title/author → else 400 :80 |
| R10 | GET /health | ✓ implemented | `src/books/core.clj:69-70` — `{:status "ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md:1-27` — install, `clojure -M:run`, env vars, routes |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test/books/core_test.clj` — 3 deftest; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (inline gate output) — build/test/lint not re-run per skill step 2.

```text
scores.json
test_coverage   = 1.0   (build + all tests passed)
code_quality    = 0.95
defect_rate     = 0.733
maintainability = 1.0
idiomatic       = 0.8
```

```text
clojure -M:test  (books.test-runner → clojure.test)
3 deftest: health-and-empty-list, create-read-filter-and-delete, validation-and-update
0 skipped / 0 disabled (no ^:skip, (comment, or with-redefs skip markers)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 177 (core 113 / test 64) |
| Files | 3 |
| Dependencies | 4 (clojure, data.json, sqlite-jdbc, ring-jetty) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All 12 pinned requirements implemented, build+tests pass, no skipped/disabled tests.

Notes (not deductions):
- PUT is a full replacement — omitted optional fields are cleared. Documented in `README.md:9`; tests assert it (`core_test.clj:53`).
- Non-numeric `/books/{id}` falls through to a 404 (`book-id` :60-62 returns nil), which is reasonable.

## Reproduce

```bash
cd experiments/adrianco/experiment-92-terra61-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=clojure_model=gpt-6.1-terra_prompt=neutral/rep1
cat scores.json                      # stored build/test/lint scores (not re-run)
cat ../../../REQUIREMENTS.json        # pinned 12-requirement checklist
clojure -M:test                       # 3 tests, all pass (only if re-verifying)
```
