# Evaluation: language=clojure_model=opus_tooling=beads · rep 1

## Summary

- **Factors:** language=clojure, model=opus, tooling=beads
- **Status:** failed (no source code — workspace contains only skeleton/config files)
- **Requirements:** 1/12 implemented, 0 partial, 11 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective)
- **Build:** unavailable — no source code to build
- **Lint:** unavailable — no source code to lint
- **Architecture:** summary skill unavailable (no source code to analyze)
- **Findings:** 12 items in `findings.jsonl` (11 critical, 1 high)

## Note on Stored Scores

The retort.db scores for this run (test_coverage=1.0, code_quality=0.833, defect_rate=1.0) **contradict** the actual workspace state. The archived workspace contains zero `.clj` source files — only project config (`deps.edn`), documentation (`README.md`), and retort metadata. The scores may have been computed against a transient workspace that was not fully archived, or against a different run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✗ missing | No .clj files in workspace; `src/books/handler.clj` absent |
| R2 | GET /books lists all books | ✗ missing | No .clj files in workspace |
| R3 | GET /books ?author= filter | ✗ missing | No .clj files in workspace |
| R4 | GET /books/{id} single book | ✗ missing | No .clj files in workspace |
| R5 | PUT /books/{id} updates book | ✗ missing | No .clj files in workspace |
| R6 | DELETE /books/{id} deletes book | ✗ missing | No .clj files in workspace |
| R7 | SQLite embedded DB storage | ✗ missing | `deps.edn` declares sqlite-jdbc dep but no code uses it |
| R8 | JSON responses + HTTP status codes | ✗ missing | No .clj files in workspace |
| R9 | Input validation (title/author required) | ✗ missing | No .clj files in workspace |
| R10 | GET /health endpoint | ✗ missing | No .clj files in workspace |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` documents JDK/Clojure prereqs, run/test commands, endpoints |
| R12 | At least 3 tests | ✗ missing | No test files; `test/books/handler_test.clj` absent |

## Build & Test

```text
Build: not attempted — no source code exists in the workspace
```

```text
Tests: not attempted — no test files exist in the workspace
```

Stored scores from retort.db (contradicted by workspace state):
- test_coverage = 1.0
- code_quality = 0.833
- defect_rate = 1.0
- maintainability = 0.950
- idiomatic = 0.760
- token_efficiency = 0.500

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 |
| Files | 8 (all config/docs) |
| Dependencies | 8 (declared in deps.edn) |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | N/A |
| Build duration | N/A |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] POST /books endpoint missing — no source code
2. [critical] GET /books list endpoint missing — no source code
3. [critical] GET /books ?author= filter missing — no source code
4. [critical] GET /books/{id} endpoint missing — no source code
5. [critical] PUT /books/{id} endpoint missing — no source code

11 of 12 findings are critical severity — the entire implementation is absent from the archived workspace. Only R11 (README) is satisfied.

## Reproduce

```bash
cd experiment-1/runs/language=clojure_model=opus_tooling=beads/rep1
find . -name "*.clj" -o -name "*.cljc"   # confirms no source files
cat deps.edn                               # shows declared but unused dependencies
cat README.md                              # references nonexistent source files
```
