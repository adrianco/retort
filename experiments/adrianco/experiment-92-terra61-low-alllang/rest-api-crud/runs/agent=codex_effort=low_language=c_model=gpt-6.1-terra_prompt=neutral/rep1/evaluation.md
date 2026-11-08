# Evaluation: agent=codex effort=low language=c model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=c, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass (gcc/cc via `make`) — `test_coverage=1.0` ⇒ build + tests succeeded (not re-run)
- **Lint:** pass — `code_quality=0.78` from `scores.json`; `-Wall -Wextra -Wpedantic -std=c11`
- **Architecture:** single-file C HTTP/1.1 server (`server.c`) over SQLite via json-c; summary skill unavailable
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.c:64-76` INSERT, returns 201 + saved object |
| R2 | GET /books lists all | ✓ implemented | `server.c:60` array ordered by id |
| R3 | GET /books ?author= filter | ✓ implemented | `server.c:56-59` binds `author=?` |
| R4 | GET /books/{id} single | ✓ implemented | `server.c:61` 200 / 404 on miss |
| R5 | PUT /books/{id} update | ✓ implemented | `server.c:72-76` UPDATE, 404 if no row changed |
| R6 | DELETE /books/{id} | ✓ implemented | `server.c:63` DELETE, 404 if no change |
| R7 | SQLite storage | ✓ implemented | `server.c:83` CREATE TABLE books; file-backed DB |
| R8 | JSON + HTTP status codes | ✓ implemented | `server.c:18-26` respond(); 200/201/400/404/405/413/500 |
| R9 | title/author required | ✓ implemented | `server.c:69-71` rejects empty/blank/non-string → 400 |
| R10 | GET /health | ✓ implemented | `server.c:51` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — deps, `make`, run, env vars, curl examples |
| R12 | ≥3 tests | ✓ implemented | `test_api.py` — 4 test methods, all pass |

## Build & Test

Not re-run — stored mechanical scores used per skill (scores.json present).

```text
make            # cc -O2 -Wall -Wextra -Wpedantic -std=c11 ... -> books-api
# test_coverage=1.0, defect_rate=1.0  => build + all tests passed
```

```text
make test       # python3 -m unittest -v test_api.py
# 4 tests: test_health, test_crud_and_filter, test_validation_and_missing, test_persistence
# 0 skipped, 0 failed (grep: 0 skip markers)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 163 (server.c 88, test_api.py 75) |
| Files (source) | 5 (server.c, test_api.py, Makefile, README.md, .gitignore) |
| Dependencies | sqlite3, json-c, pkg-config (system libs) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

Stored scores: code_quality=0.78, maintainability=0.67, idiomatic=0.25, token_efficiency=0.009.

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Server handles one connection at a time (synchronous accept loop) — not required by spec.

No requirement, build, test, or lint defects.

## Reproduce

```bash
cd "experiments/adrianco/experiment-92-terra61-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=c_model=gpt-6.1-terra_prompt=neutral/rep1"
cat scores.json                      # test_coverage=1.0 => build + tests passed
cat ../../../REQUIREMENTS.json        # pinned 12-requirement checklist
grep -cE "def test_" test_api.py      # 4 tests
grep -cE "skip|SkipTest" test_api.py  # 0 skips
```
