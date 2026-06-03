# Evaluation: language=clojure_model=sonnet_tooling=beads · rep 2

## Summary

- **Factors:** language=clojure, model=sonnet, tooling=beads
- **Status:** failed (no source code produced — agent only generated config/documentation files)
- **Requirements:** 0/12 implemented, 1 partial, 11 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective)
- **Build:** unavailable — no source code to build
- **Lint:** unavailable — no source code to lint
- **Architecture:** no source code to analyze
- **Findings:** 13 items in `findings.jsonl` (9 critical, 3 high, 1 medium)

**Note on stored scores:** retort.db reports test_coverage=1.0 and defect_rate=1.0 for this run (run_id=69). These are false positives — the test runner succeeded vacuously because no source files or test files exist. The scorer measured "zero failures" rather than "all tests pass."

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|-----|-----|----|
| R1 | POST /books creates a new book | ✗ missing | No src/ directory or .clj files in workspace |
| R2 | GET /books lists all books | ✗ missing | No src/ directory or .clj files in workspace |
| R3 | GET /books supports ?author= filter | ✗ missing | No src/ directory or .clj files in workspace |
| R4 | GET /books/{id} returns a single book | ✗ missing | No src/ directory or .clj files in workspace |
| R5 | PUT /books/{id} updates a book | ✗ missing | No src/ directory or .clj files in workspace |
| R6 | DELETE /books/{id} deletes a book | ✗ missing | No src/ directory or .clj files in workspace |
| R7 | Data stored in SQLite | ✗ missing | deps.edn lists next.jdbc/sqlite-jdbc but no code uses them |
| R8 | JSON responses with appropriate HTTP status codes | ✗ missing | No src/ directory or .clj files in workspace |
| R9 | Input validation: title and author required | ✗ missing | No src/ directory or .clj files in workspace |
| R10 | GET /health health-check endpoint | ✗ missing | No src/ directory or .clj files in workspace |
| R11 | README.md with setup and run instructions | ~ partial | README.md exists and is well-written but describes code that was never created |
| R12 | At least 3 unit/integration tests | ✗ missing | No test/ directory or test files; deps.edn :test alias has no code to run |

## Build & Test

```text
No build or test execution possible — no source code files exist in the workspace.
The agent produced only: deps.edn, README.md, AGENTS.md, CLAUDE.md, .gitignore
No src/ directory, no .clj files, no test/ directory.
```

```text
Stored scores from retort.db (run_id=69):
  test_coverage    = 1.0  (false positive — no tests exist)
  code_quality     = 0.833
  defect_rate      = 1.0  (false positive — no code to have defects)
  maintainability  = 0.971
  idiomatic        = 0.78
  token_efficiency = 0.5
  bead_usage_score = 1.0
  findings         = 0.99
  _duration_seconds = 211.15
  _tokens          = 618307
  _cost_usd        = 0.437
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 |
| Lines of config (deps.edn) | 16 |
| Files | 8 (all config/docs) |
| Dependencies (declared) | 8 (in deps.edn, unused) |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | N/A |
| Build duration | N/A |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] No source code produced — agent only generated config and documentation files
2. [critical] No POST /books endpoint — no source code exists
3. [critical] No GET /books/{id} endpoint — no source code exists
4. [critical] No PUT /books/{id} endpoint — no source code exists
5. [critical] No DELETE /books/{id} endpoint — no source code exists

## Reproduce

```bash
cd experiment-1/runs/language=clojure_model=sonnet_tooling=beads/rep2
# Verify no source code:
find . -name "*.clj" -o -name "*.cljc" -o -name "*.cljs"   # returns nothing
ls src/    # directory does not exist
ls test/   # directory does not exist
# Check what exists:
ls -la     # deps.edn, README.md, AGENTS.md, CLAUDE.md, .gitignore, stack.json, TASK.md, _meta.json
```
